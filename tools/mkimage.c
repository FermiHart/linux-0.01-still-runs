/*
 * mkimage.c — build a bootable HD image for linux-0.01-still-runs.
 *
 * F E R M I ∞ H A R T
 *
 * Produces a raw disk image laid out as:
 *
 *   sector 0          MBR (table + 0x55AA)
 *   sector 1..        partition #1: Minix v1 filesystem
 *
 * The Minix v1 filesystem we craft by hand (no mkfs.minix dep —
 * it's blocked in this sandbox anyway). Layout per Tanenbaum:
 *
 *   block 0   boot block (zeros)
 *   block 1   super_block  (magic 0x137F, BLOCK_SIZE=1024)
 *   block 2   inode bitmap (imap)
 *   block 3   zone  bitmap (zmap)
 *   block 4   inode table  (32 inodes/block, d_inode = 32 bytes)
 *   ...
 *   block N   first data zone
 *
 * Linus' kernel calls sys_setup() which reads the MBR and mounts
 * partition #1. So we set partition_table[0].start_sect = 1 and
 * make ROOT_DEV / dev[1+5*0] in fs/super.c land on us.
 *
 * Files we install:
 *   /                directory
 *   /bin             directory
 *   /dev             directory
 *   /dev/tty0        char device (major=4, minor=0)
 *
 * Any additional files passed as args are placed under /bin/.
 *
 * Build:  gcc -O2 -o mkimage mkimage.c
 * Run:    mkimage <out.img> [file1.bin file2.bin ...]
 *
 * Each file is wrapped with an a.out ZMAGIC header and placed
 * at /bin/<filename_without_ext>.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <limits.h>
#include <unistd.h>

#include "../bemu/experience.h"
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>

#define BLOCK_SIZE      1024
#define SECTOR_SIZE     512
#define BLOCKS_PER_SEC  (BLOCK_SIZE / SECTOR_SIZE)

/* match include/linux/fs.h on the kernel side */
#define NAME_LEN        14
#define SUPER_MAGIC     0x137F

/* Inode bits — match include/sys/stat.h + include/const.h */
#ifndef S_IFREG
#define S_IFREG  0100000
#endif
#ifndef S_IFDIR
#define S_IFDIR  0040000
#endif
#ifndef S_IFCHR
#define S_IFCHR  0020000
#endif

/* a.out ZMAGIC header — match include/a.out.h */
struct a_out_header {
    uint32_t a_magic;
    uint32_t a_text;
    uint32_t a_data;
    uint32_t a_bss;
    uint32_t a_syms;
    uint32_t a_entry;
    uint32_t a_trsize;
    uint32_t a_drsize;
};
#define ZMAGIC 0413
#define A_TXTOFF BLOCK_SIZE   /* exec.c hardcodes this */

/* Minix v1 on-disk structures (kernel side: struct d_inode in fs.h) */
struct minix_super {
    uint16_t s_ninodes;
    uint16_t s_nzones;
    uint16_t s_imap_blocks;
    uint16_t s_zmap_blocks;
    uint16_t s_firstdatazone;
    uint16_t s_log_zone_size;
    uint32_t s_max_size;
    uint16_t s_magic;
};

struct minix_inode {
    uint16_t i_mode;
    uint16_t i_uid;
    uint32_t i_size;
    uint32_t i_time;
    uint8_t  i_gid;
    uint8_t  i_nlinks;
    uint16_t i_zone[9];
};

struct minix_dirent {
    uint16_t inode;
    char     name[NAME_LEN];
};

/* MBR partition entry */
struct mbr_part {
    uint8_t  boot_ind;
    uint8_t  head;
    uint8_t  sector;
    uint8_t  cyl;
    uint8_t  sys_ind;
    uint8_t  end_head;
    uint8_t  end_sector;
    uint8_t  end_cyl;
    uint32_t start_sect;
    uint32_t nr_sects;
} __attribute__((packed));

#define STATIC_ASSERT(name, expression) \
    typedef char static_assert_##name[(expression) ? 1 : -1]

STATIC_ASSERT(a_out_header_size, sizeof(struct a_out_header) == 32);
STATIC_ASSERT(a_out_header_entry, offsetof(struct a_out_header, a_entry) == 20);
STATIC_ASSERT(eight_bit_bytes, CHAR_BIT == 8);
STATIC_ASSERT(minix_super_max_size, offsetof(struct minix_super, s_max_size) == 12);
STATIC_ASSERT(minix_super_magic, offsetof(struct minix_super, s_magic) == 16);
STATIC_ASSERT(minix_inode_size, sizeof(struct minix_inode) == 32);
STATIC_ASSERT(minix_inode_zones, offsetof(struct minix_inode, i_zone) == 14);
STATIC_ASSERT(minix_dirent_size, sizeof(struct minix_dirent) == 16);
STATIC_ASSERT(mbr_part_size, sizeof(struct mbr_part) == 16);
STATIC_ASSERT(mbr_part_start, offsetof(struct mbr_part, start_sect) == 8);

/* ------------------------------------------------------------------ */

#define die(...) do { fprintf(stderr, "mkimage: " __VA_ARGS__); \
                      fputc('\n', stderr); exit(1); } while (0)

static uint8_t *fs_img;
static uint64_t fs_size;
static struct minix_super *sb;

#define BLOCK(n)  (fs_img + (uint64_t)(n) * BLOCK_SIZE)

#define NZONES       1024
#define IMAP_BLOCKS  1
#define ZMAP_BLOCKS  1
#define INODE_BLOCKS 8
#define INODES_PER_BLOCK (BLOCK_SIZE / 32)
#define NINODES      (INODE_BLOCKS * INODES_PER_BLOCK)
#define FIRST_DATA_ZONE (2 + IMAP_BLOCKS + ZMAP_BLOCKS + INODE_BLOCKS)

STATIC_ASSERT(inodes_fit_disk_field, NINODES <= UINT16_MAX);
STATIC_ASSERT(zones_fit_disk_field, NZONES <= UINT16_MAX);

static int next_inode = 1;
static int next_zone  = FIRST_DATA_ZONE;

static uint16_t get_le16(const void *ptr)
{
    const uint8_t *p = ptr;
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t get_le32(const void *ptr)
{
    const uint8_t *p = ptr;
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void put_le16(void *ptr, uint16_t value)
{
    uint8_t *p = ptr;
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
}

static void put_le32(void *ptr, uint32_t value)
{
    uint8_t *p = ptr;
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
    p[2] = (uint8_t)(value >> 16);
    p[3] = (uint8_t)(value >> 24);
}

static void set_bit(uint8_t *bmap, int bit)
{
    bmap[bit >> 3] |= (uint8_t)(1u << (bit & 7));
}

static int alloc_inode(void)
{
    int n;
    if (next_inode >= NINODES) die("out of inodes");
    n = next_inode++;
    set_bit(BLOCK(2), n);
    return n;
}

static int alloc_zone(void)
{
    int z;
    if (next_zone >= NZONES) die("out of zones");
    z = next_zone++;
    set_bit(BLOCK(3), z - (FIRST_DATA_ZONE - 1));
    return z;
}

static struct minix_inode *get_inode(int nr)
{
    int blk = 2 + IMAP_BLOCKS + ZMAP_BLOCKS + (nr - 1) / INODES_PER_BLOCK;
    int off = (nr - 1) % INODES_PER_BLOCK;
    return (struct minix_inode *)(BLOCK(blk) + off * 32);
}

static int write_data_block(const void *data, size_t len)
{
    int z;
    if (len > BLOCK_SIZE)
        die("data block overflow (%zu > %d)", len, BLOCK_SIZE);
    z = alloc_zone();
    memcpy(BLOCK(z), data, len);
    return z;
}

static size_t file_zone_count(size_t len)
{
    size_t data_zones = len / BLOCK_SIZE + (len % BLOCK_SIZE != 0);
    size_t zones = data_zones;

    if (data_zones > 7) zones++; /* single-indirect table */
    if (data_zones > 7 + BLOCK_SIZE / sizeof(uint16_t)) {
        size_t double_zones = data_zones - 7 - BLOCK_SIZE / sizeof(uint16_t);
        size_t indirect_tables = double_zones / (BLOCK_SIZE / sizeof(uint16_t)) +
                                 (double_zones % (BLOCK_SIZE / sizeof(uint16_t)) != 0);
        if (zones > SIZE_MAX - 1 - indirect_tables)
            die("file zone count overflow");
        zones += 1 + indirect_tables; /* double-indirect table and its children */
    }
    return zones;
}

static void check_file_capacity(size_t len, const char *description)
{
    size_t needed = file_zone_count(len);
    size_t available = (size_t)(NZONES - next_zone);

    if (needed > available)
        die("%s needs %zu zones, only %zu remain", description, needed, available);
}

static void add_dirent(int dir_ino, const char *name, int target_ino)
{
    struct minix_inode *dir = get_inode(dir_ino);
    size_t name_len = strlen(name);
    int z = get_le16(&dir->i_zone[0]);
    uint32_t dir_size;
    if (!z) die("dir inode %d has no first zone", dir_ino);
    if (name_len == 0 || name_len > NAME_LEN || strchr(name, '/'))
        die("invalid Minix name '%s'", name);
    if (target_ino <= 0 || target_ino > UINT16_MAX)
        die("directory inode number is out of range: %d", target_ino);
    struct minix_dirent *de = (struct minix_dirent *)BLOCK(z);
    size_t slots = BLOCK_SIZE / sizeof(*de);
    for (size_t i = 0; i < slots; i++) {
        if (get_le16(&de[i].inode) != 0 &&
            memcmp(de[i].name, name, name_len) == 0 &&
            (name_len == NAME_LEN || de[i].name[name_len] == 0))
            die("duplicate directory name '%s'", name);
    }
    for (size_t i = 0; i < slots; i++) {
        if (get_le16(&de[i].inode) == 0) {
            put_le16(&de[i].inode, (uint16_t)target_ino);
            memset(de[i].name, 0, NAME_LEN);
            memcpy(de[i].name, name, name_len);
            dir_size = get_le32(&dir->i_size);
            if (dir_size > BLOCK_SIZE - sizeof(*de))
                die("directory size overflow");
            put_le32(&dir->i_size, dir_size + (uint32_t)sizeof(*de));
            return;
        }
    }
    die("directory full");
}

static int mkdir_inode(int parent_ino)
{
    int ino = alloc_inode();
    struct minix_inode *in = get_inode(ino);
    put_le16(&in->i_mode, (uint16_t)(S_IFDIR | 0755));
    put_le16(&in->i_uid, 0);
    in->i_gid  = 0;
    in->i_nlinks = 2;
    put_le32(&in->i_time, 0);
    put_le16(&in->i_zone[0], (uint16_t)alloc_zone());
    put_le32(&in->i_size, 0);

    if (parent_ino == 0) parent_ino = ino;
    add_dirent(ino, ".",  ino);
    add_dirent(ino, "..", parent_ino);
    return ino;
}

static int mkfile_inode_mode(const void *data, size_t len, int mode)
{
    if (len > UINT32_MAX) die("file too large (%zu bytes)", len);
    check_file_capacity(len, "file");
    int ino = alloc_inode();
    struct minix_inode *in = get_inode(ino);
    put_le16(&in->i_mode, (uint16_t)(S_IFREG | mode));
    put_le16(&in->i_uid, 0);
    in->i_gid  = 0;
    in->i_nlinks = 1;
    put_le32(&in->i_size, (uint32_t)len);
    put_le32(&in->i_time, 0);

    const uint8_t *p = data;
    size_t left = len;
    for (int i = 0; i < 7 && left > 0; i++) {
        size_t chunk = left < BLOCK_SIZE ? left : BLOCK_SIZE;
        put_le16(&in->i_zone[i], (uint16_t)write_data_block(p, chunk));
        p    += chunk;
        left -= chunk;
    }
    if (left > 0) {
        int ind = alloc_zone();
        uint8_t *zones = BLOCK(ind);
        put_le16(&in->i_zone[7], (uint16_t)ind);
        for (size_t i = 0; i < BLOCK_SIZE / sizeof(uint16_t) && left > 0; i++) {
            size_t chunk = left < BLOCK_SIZE ? left : BLOCK_SIZE;
            put_le16(zones + i * sizeof(uint16_t),
                     (uint16_t)write_data_block(p, chunk));
            p += chunk;
            left -= chunk;
        }
    }
    if (left > 0) {
        int dind = alloc_zone();
        uint8_t *dtable = BLOCK(dind);
        put_le16(&in->i_zone[8], (uint16_t)dind);
        for (size_t d = 0; d < BLOCK_SIZE / sizeof(uint16_t) && left > 0; d++) {
            int ind = alloc_zone();
            uint8_t *zones = BLOCK(ind);
            put_le16(dtable + d * sizeof(uint16_t), (uint16_t)ind);
            for (size_t i = 0; i < BLOCK_SIZE / sizeof(uint16_t) && left > 0; i++) {
                size_t chunk = left < BLOCK_SIZE ? left : BLOCK_SIZE;
                put_le16(zones + i * sizeof(uint16_t),
                         (uint16_t)write_data_block(p, chunk));
                p += chunk;
                left -= chunk;
            }
        }
    }
    if (left > 0) die("file too big for double indirect blocks");
    return ino;
}

static int mkfile_inode(const void *data, size_t len)
{
    return mkfile_inode_mode(data, len, 0755);
}

static int mkchr_inode(int major, int minor)
{
    if (major < 0 || major > UINT8_MAX || minor < 0 || minor > UINT8_MAX)
        die("device number is out of range: %d,%d", major, minor);
    int ino = alloc_inode();
    struct minix_inode *in = get_inode(ino);
    put_le16(&in->i_mode, (uint16_t)(S_IFCHR | 0666));
    put_le16(&in->i_uid, 0);
    in->i_gid = 0;
    in->i_nlinks = 1;
    put_le32(&in->i_size, 0);
    put_le32(&in->i_time, 0);
    put_le16(&in->i_zone[0], (uint16_t)((major << 8) | (minor & 0xff)));
    return ino;
}

static int add_dir(int parent_ino, const char *name)
{
    int ino = mkdir_inode(parent_ino);
    struct minix_inode *parent = get_inode(parent_ino);
    add_dirent(parent_ino, name, ino);
    if (parent->i_nlinks == UINT8_MAX) die("directory link count overflow");
    parent->i_nlinks++;
    return ino;
}

static int add_file(int parent_ino, const char *name, const char *data, int mode)
{
    int ino = mkfile_inode_mode(data, strlen(data), mode);
    add_dirent(parent_ino, name, ino);
    return ino;
}

static int add_chr(int parent_ino, const char *name, int major, int minor)
{
    int ino = mkchr_inode(major, minor);
    add_dirent(parent_ino, name, ino);
    return ino;
}

static void read_full(int fd, uint8_t *buf, size_t len, const char *path)
{
    size_t done = 0;
    while (done < len) {
        size_t chunk = len - done;
        if (chunk > 1024 * 1024) chunk = 1024 * 1024;
        ssize_t n = read(fd, buf + done, chunk);
        if (n > 0) {
            done += (size_t)n;
            continue;
        }
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) die("read %s: %s", path, strerror(errno));
        die("short read on %s (%zu of %zu bytes)", path, done, len);
    }
}

static void *wrap_aout(const char *path, size_t *out_len)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0) die("open %s: %s", path, strerror(errno));
    struct stat st;
    if (fstat(fd, &st) < 0) die("fstat %s: %s", path, strerror(errno));
    if (!S_ISREG(st.st_mode)) die("%s: input is not a regular file", path);
    if (st.st_size < 0 || (uintmax_t)st.st_size > UINT32_MAX ||
        (uintmax_t)st.st_size > SIZE_MAX)
        die("%s: input size is out of range", path);
    size_t text = (size_t)st.st_size;
    if (text > SIZE_MAX - A_TXTOFF)
        die("%s: wrapped size overflows size_t", path);
    size_t total = A_TXTOFF + text;
    if (total > UINT32_MAX)
        die("%s: wrapped size exceeds the Minix inode size field", path);
    check_file_capacity(total, path);
    uint8_t *buf = calloc(1, total);
    if (!buf) die("oom");
    struct a_out_header *h = (struct a_out_header *)buf;
    put_le32(&h->a_magic, ZMAGIC);
    put_le32(&h->a_text, (uint32_t)text);
    put_le32(&h->a_data, 0);
    put_le32(&h->a_bss, 0x10000);
    put_le32(&h->a_syms, 0);
    put_le32(&h->a_entry, 0);
    put_le32(&h->a_trsize, 0);
    put_le32(&h->a_drsize, 0);
    read_full(fd, buf + A_TXTOFF, text, path);
    if (close(fd) < 0) die("close %s: %s", path, strerror(errno));
    *out_len = total;
    return buf;
}

/* Preserve the original 14-byte truncation, then strip the first extension. */
static void transformed_name(const char *path, char out[NAME_LEN + 1])
{
    const char *base = strrchr(path, '/');
    size_t len;
    base = base ? base + 1 : path;
    len = strcspn(base, ".");
    if (len > NAME_LEN) len = NAME_LEN;
    if (len == 0)
        die("%s: transformed name is empty", path);
    memcpy(out, base, len);
    out[len] = 0;
    if (strcmp(out, ".") == 0 || strcmp(out, "..") == 0)
        die("%s: invalid transformed name '%s'", path, out);
}

static int write_full(int fd, const uint8_t *buf, size_t len)
{
    size_t done = 0;
    while (done < len) {
        size_t chunk = len - done;
        if (chunk > 1024 * 1024) chunk = 1024 * 1024;
        ssize_t n = write(fd, buf + done, chunk);
        if (n > 0) {
            done += (size_t)n;
            continue;
        }
        if (n < 0 && errno == EINTR) continue;
        if (n == 0) errno = EIO;
        return -1;
    }
    return 0;
}

static void publish_fail(const char *tmp_path, int fd, const char *operation)
{
    int saved = errno;
    if (fd >= 0) (void)close(fd);
    (void)unlink(tmp_path);
    errno = saved;
    die("%s: %s", operation, strerror(errno));
}

static int destination_status(const char *path, struct stat *st)
{
    int result;

    do {
        result = lstat(path, st);
    } while (result < 0 && errno == EINTR);
    if (result == 0) {
        if (!S_ISREG(st->st_mode)) {
            errno = S_ISLNK(st->st_mode) ? ELOOP : EINVAL;
            return -1;
        }
        return 1;
    }
    if (errno == ENOENT) return 0;
    return -1;
}

static void sync_parent_directory(const char *path)
{
    const char *slash = strrchr(path, '/');
    const char *directory = ".";
    char *allocated = NULL;
    size_t length;
    int fd;
    int saved;

    if (slash) {
        length = slash == path ? 1 : (size_t)(slash - path);
        allocated = malloc(length + 1);
        if (!allocated) die("oom for output directory path");
        memcpy(allocated, path, length);
        allocated[length] = '\0';
        directory = allocated;
    }
    do {
        fd = open(directory, O_RDONLY | O_DIRECTORY);
    } while (fd < 0 && errno == EINTR);
    if (fd < 0)
        die("open output directory %s: %s", directory, strerror(errno));
    while (fsync(fd) < 0) {
        if (errno == EINTR) continue;
        saved = errno;
        (void)close(fd);
        errno = saved;
        die("fsync output directory %s: %s", directory, strerror(errno));
    }
    if (close(fd) < 0)
        die("close output directory %s: %s", directory, strerror(errno));
    free(allocated);
}

static void publish_image(const char *out_path, const uint8_t *disk, size_t len)
{
    static const char suffix[] = ".tmp.XXXXXX";
    size_t out_len = strlen(out_path);
    char *tmp_path;
    int fd;
    int expected_status;
    int current_status;
    struct stat expected;
    struct stat current;

    if (out_len == 0) die("output path is empty");
    expected_status = destination_status(out_path, &expected);
    if (expected_status < 0)
        die("refusing output destination %s: %s", out_path, strerror(errno));

    if (out_len > SIZE_MAX - sizeof(suffix))
        die("output path is too long");
    tmp_path = malloc(out_len + sizeof(suffix));
    if (!tmp_path) die("oom for temporary output path");
    memcpy(tmp_path, out_path, out_len);
    memcpy(tmp_path + out_len, suffix, sizeof(suffix));

    fd = mkstemp(tmp_path);
    if (fd < 0) die("create temporary image beside %s: %s",
                    out_path, strerror(errno));
    if (fstat(fd, &current) < 0)
        publish_fail(tmp_path, fd, "fstat temporary image");
    if (!S_ISREG(current.st_mode)) {
        errno = EINVAL;
        publish_fail(tmp_path, fd, "temporary image is not a regular file");
    }
    if (write_full(fd, disk, len) < 0)
        publish_fail(tmp_path, fd, "write temporary image");
    if (fchmod(fd, 0644) < 0)
        publish_fail(tmp_path, fd, "chmod temporary image");
    while (fsync(fd) < 0) {
        if (errno == EINTR) continue;
        publish_fail(tmp_path, fd, "fsync temporary image");
    }
    if (close(fd) < 0)
        publish_fail(tmp_path, -1, "close temporary image");
    current_status = destination_status(out_path, &current);
    if (current_status < 0)
        publish_fail(tmp_path, -1, "refusing changed output destination");
    if (current_status != expected_status ||
        (current_status != 0 &&
         (current.st_dev != expected.st_dev || current.st_ino != expected.st_ino))) {
        errno = current_status == 0 ? ENOENT : EBUSY;
        publish_fail(tmp_path, -1, "output destination changed during build");
    }
    do {
        fd = rename(tmp_path, out_path);
    } while (fd < 0 && errno == EINTR);
    if (fd < 0)
        publish_fail(tmp_path, -1, "rename temporary image");
    sync_parent_directory(out_path);
    free(tmp_path);
}

/* ------------------------------------------------------------------ */
int main(int argc, char **argv)
{
    int experience_1991 = 0;
    int first_path = 1;
    if (argc > 1 && strcmp(argv[1], "--experience") == 0) {
        if (argc < 4 || strcmp(argv[2], "1991") != 0)
            die("usage: %s [--experience 1991] out.img [file.bin ...]", argv[0]);
        experience_1991 = 1;
        first_path = 3;
    }
    if (argc <= first_path)
        die("usage: %s [--experience 1991] out.img [file.bin ...]", argv[0]);
    const char *out_path = argv[first_path];
    size_t n_files = (size_t)(argc - first_path - 1);
    char **file_paths = argv + first_path + 1;
    char (*names)[NAME_LEN + 1] = NULL;

    if (n_files > 0) {
        if (n_files > SIZE_MAX / sizeof(*names))
            die("too many input files");
        names = calloc(n_files, sizeof(*names));
        if (!names) die("oom for transformed names");
    }
    for (size_t i = 0; i < n_files; i++) {
        transformed_name(file_paths[i], names[i]);
        for (size_t j = 0; j < i; j++) {
            if (strcmp(names[i], names[j]) == 0)
                die("%s and %s collide as 14-byte Minix name '%s'",
                    file_paths[j], file_paths[i], names[i]);
        }
    }

    fs_size = (uint64_t)NZONES * BLOCK_SIZE;
    if (fs_size > SIZE_MAX) die("filesystem image is too large for this host");
    fs_img = calloc(1, (size_t)fs_size);
    if (!fs_img) die("oom (%llu)", (unsigned long long)fs_size);

    sb = (struct minix_super *)BLOCK(1);
    put_le16(&sb->s_ninodes, NINODES);
    put_le16(&sb->s_nzones, NZONES);
    put_le16(&sb->s_imap_blocks, IMAP_BLOCKS);
    put_le16(&sb->s_zmap_blocks, ZMAP_BLOCKS);
    put_le16(&sb->s_firstdatazone, FIRST_DATA_ZONE);
    put_le16(&sb->s_log_zone_size, 0);
    put_le32(&sb->s_max_size, 0x10081C00);
    put_le16(&sb->s_magic, SUPER_MAGIC);

    set_bit(BLOCK(2), 0);
    set_bit(BLOCK(3), 0);

    int root_ino = mkdir_inode(0);
    if (root_ino != 1) die("root ino isn't 1?!");

    int bin_ino = add_dir(root_ino, "bin");
    int dev_ino = add_dir(root_ino, "dev");
    int etc_ino = add_dir(root_ino, "etc");
    int home_ino = add_dir(root_ino, "home");
    if (!experience_1991)
        add_dir(home_ino, "fermihart");
    add_dir(root_ino, "tmp");

	add_file(etc_ino, "fstab", "/dev/hd1 / minix rw 0 0\n", 0644);
	if (experience_1991) {
		add_file(etc_ino, "passwd", "root:x:0:0:root:/:/bin/shell\n", 0644);
		add_file(etc_ino, "issue", "Linux 0.01 historical experience\n", 0644);
		add_file(etc_ino, "motd",
			"Linux 0.01\n"
			"\n"
			"Experience profile: 1991\n"
			"8 MiB RAM, Minix v1 filesystem, and a small Unix shell.\n",
			0644);
	} else {
		add_file(etc_ino, "passwd", "root:x:0:0:root:/home/fermihart:/bin/shell\n", 0644);
		add_file(etc_ino, "issue",
		"Linux 0.01 alive experience\n"
		"Try: ls -la, cat /etc/fstab, whoami, mount, df, ps aux\n", 0644);
		add_file(etc_ino, "motd",
		"Vesica Piscis alive experience\n"
		"\n"
		"There is a specific feeling that comes from booting an operating\n"
		"system written three and a half decades ago. It is not nostalgia\n"
		"-- nostalgia implies distance, the safe view from behind glass.\n"
		"This is something else. This is the moment when the machine you\n"
		"built in 2026 loads a kernel whose ideas were typed out in a\n"
		"Helsinki bedroom, on a 386 with 33 megahertz and four megabytes\n"
		"of RAM, and it works.\n"
		"\n"
		"Not works in the sense of a museum exhibit under rope and velvet.\n"
		"Works in the sense that you can type a command, create a directory,\n"
		"write a file, read it back, and feel the same feedback loop that\n"
		"Linus described in his 25 August 1991 comp.os.minix post:\n"
		"\n"
		"  I'm doing a (free) operating system (just a hobby, won't be\n"
		"  big and professional).\n"
		"\n"
		"He was wrong about the scale. But he was right about the spirit.\n"
		"\n"
		"This project exists to keep that spirit running, not frozen behind\n"
		"a glass pane. The historical linux-0.01 core is still here, still\n"
		"recognizable, still the heart of the machine. What we added is a\n"
		"firmware-free KVM bridge with emulated legacy devices, a toolchain\n"
		"that speaks 2026 C while respecting 1991 conventions, and documented\n"
		"runtime patches that expose rather than hide changed assumptions.\n"
		"\n"
		"The experience we tried to bring back alive is the one Linus\n"
		"described: you sit at a terminal, you type, the machine answers.\n"
		"There is no container orchestration between you and the process\n"
		"table. There is no init system with seventy stages. There is a\n"
		"kernel, a console, a shell, and you.\n"
		"\n"
		"Welcome to 1991. It still runs in 2026.\n", 0644);
	}
	add_chr(dev_ino, "tty0", 4, 0);

    for (size_t i = 0; i < n_files; i++) {
        size_t len;
        void *buf = wrap_aout(file_paths[i], &len);
        int ino = mkfile_inode(buf, len);
        add_dirent(bin_ino, names[i], ino);
        fprintf(stderr, "  added /bin/%-12s (%zu bytes, inode %d)\n",
                names[i], len, ino);
        free(buf);
    }

    fprintf(stderr,
        "  minix v1 fs: %d inodes used, %d zones used, first data zone = %d\n",
        next_inode - 1, next_zone - FIRST_DATA_ZONE, FIRST_DATA_ZONE);

    if (fs_size % SECTOR_SIZE) die("filesystem size is not sector aligned");
    uint64_t fs_sectors = fs_size / SECTOR_SIZE;
    if (fs_sectors == UINT64_MAX) die("disk sector count overflow");
    uint64_t disk_sectors = fs_sectors + 1;
    if (disk_sectors > UINT64_MAX / SECTOR_SIZE)
        die("disk byte size overflow");
    uint64_t disk_size = disk_sectors * SECTOR_SIZE;

    uint64_t target_total = UINT64_C(977) * 5 * 17 * 512;
    if (disk_size < target_total) disk_size = target_total;
    if (disk_size > SIZE_MAX) die("disk image is too large for this host");
    if (disk_sectors - 1 > UINT32_MAX) die("partition sector count overflow");

    uint8_t *disk = calloc(1, (size_t)disk_size);
    if (!disk) die("oom on disk image");

    struct mbr_part *p = (struct mbr_part *)(disk + 0x1BE);
    p[0].boot_ind  = 0x80;
    p[0].head      = 0;
    p[0].sector    = 2;
    p[0].cyl       = 0;
    p[0].sys_ind   = 0x81;
    p[0].end_head  = 4;
    p[0].end_sector= 17;
    p[0].end_cyl   = 0xff;
    put_le32(&p[0].start_sect, 1);
    put_le32(&p[0].nr_sects, (uint32_t)(disk_sectors - 1));
    disk[510] = 0x55;
    disk[511] = 0xAA;
    if (experience_1991)
        memcpy(disk + EXPERIENCE_IMAGE_MARKER_OFFSET,
               EXPERIENCE_IMAGE_MARKER_1991, EXPERIENCE_IMAGE_MARKER_LEN);
    else
        memcpy(disk + EXPERIENCE_IMAGE_MARKER_OFFSET,
               EXPERIENCE_IMAGE_MARKER_ALIVE, EXPERIENCE_IMAGE_MARKER_LEN);

    memcpy(disk + SECTOR_SIZE, fs_img, (size_t)fs_size);

    /* rename(2) replaces a destination symlink itself; it never follows it. */
    publish_image(out_path, disk, (size_t)disk_size);
    free(disk);
    free(fs_img);
    free(names);

    fprintf(stderr, "  wrote %s  (%llu bytes, %llu sectors)\n",
            out_path, (unsigned long long)disk_size,
            (unsigned long long)disk_sectors);
    return 0;
}
