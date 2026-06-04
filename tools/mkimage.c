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
#include <unistd.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <libgen.h>

#define BLOCK_SIZE      1024
#define SECTOR_SIZE     512
#define BLOCKS_PER_SEC  (BLOCK_SIZE / SECTOR_SIZE)

/* match include/linux/fs.h on the kernel side */
#define NAME_LEN        14
#define SUPER_MAGIC     0x137F

/* Inode bits — match include/sys/stat.h + include/const.h */
#define S_IFREG  0100000
#define S_IFDIR  0040000
#define S_IFCHR  0020000

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

static int next_inode = 1;
static int next_zone  = FIRST_DATA_ZONE;

static void set_bit(uint8_t *bmap, int bit)
{
    bmap[bit >> 3] |= (uint8_t)(1u << (bit & 7));
}

static int alloc_inode(void)
{
    int n = next_inode++;
    if (n >= NINODES) die("out of inodes");
    set_bit(BLOCK(2), n);
    return n;
}

static int alloc_zone(void)
{
    int z = next_zone++;
    if (z >= NZONES) die("out of zones");
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
    if (len > BLOCK_SIZE) die("data block overflow (%zu > %d)", len, BLOCK_SIZE);
    int z = alloc_zone();
    memcpy(BLOCK(z), data, len);
    return z;
}

static void add_dirent(int dir_ino, const char *name, int target_ino)
{
    struct minix_inode *dir = get_inode(dir_ino);
    int z = dir->i_zone[0];
    if (!z) die("dir inode %d has no first zone", dir_ino);
    struct minix_dirent *de = (struct minix_dirent *)BLOCK(z);
    int slots = BLOCK_SIZE / sizeof(*de);
    for (int i = 0; i < slots; i++) {
        if (de[i].inode == 0) {
            de[i].inode = (uint16_t)target_ino;
            memset(de[i].name, 0, NAME_LEN);
            strncpy(de[i].name, name, NAME_LEN);
            dir->i_size += sizeof(*de);
            dir->i_nlinks++;
            return;
        }
    }
    die("directory full");
}

static int mkdir_inode(int parent_ino)
{
    int ino = alloc_inode();
    struct minix_inode *in = get_inode(ino);
    in->i_mode = S_IFDIR | 0755;
    in->i_uid  = 0;
    in->i_gid  = 0;
    in->i_nlinks = 0;
    in->i_time = 0;
    in->i_zone[0] = (uint16_t)alloc_zone();
    in->i_size = 0;

    if (parent_ino == 0) parent_ino = ino;
    add_dirent(ino, ".",  ino);
    add_dirent(ino, "..", parent_ino);
    return ino;
}

static int mkfile_inode_mode(const void *data, size_t len, int mode)
{
    int ino = alloc_inode();
    struct minix_inode *in = get_inode(ino);
    in->i_mode = S_IFREG | mode;
    in->i_uid  = 0;
    in->i_gid  = 0;
    in->i_nlinks = 1;
    in->i_size = (uint32_t)len;
    in->i_time = 0;

    const uint8_t *p = data;
    size_t left = len;
    for (int i = 0; i < 7 && left > 0; i++) {
        size_t chunk = left < BLOCK_SIZE ? left : BLOCK_SIZE;
        in->i_zone[i] = (uint16_t)write_data_block(p, chunk);
        p    += chunk;
        left -= chunk;
    }
    if (left > 0) {
        int ind = alloc_zone();
        uint16_t *zones = (uint16_t *)BLOCK(ind);
        in->i_zone[7] = (uint16_t)ind;
        for (int i = 0; i < BLOCK_SIZE / (int)sizeof(uint16_t) && left > 0; i++) {
            size_t chunk = left < BLOCK_SIZE ? left : BLOCK_SIZE;
            zones[i] = (uint16_t)write_data_block(p, chunk);
            p += chunk;
            left -= chunk;
        }
    }
    if (left > 0) {
        int dind = alloc_zone();
        uint16_t *dtable = (uint16_t *)BLOCK(dind);
        in->i_zone[8] = (uint16_t)dind;
        for (int d = 0; d < BLOCK_SIZE / (int)sizeof(uint16_t) && left > 0; d++) {
            int ind = alloc_zone();
            uint16_t *zones = (uint16_t *)BLOCK(ind);
            dtable[d] = (uint16_t)ind;
            for (int i = 0; i < BLOCK_SIZE / (int)sizeof(uint16_t) && left > 0; i++) {
                size_t chunk = left < BLOCK_SIZE ? left : BLOCK_SIZE;
                zones[i] = (uint16_t)write_data_block(p, chunk);
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
    int ino = alloc_inode();
    struct minix_inode *in = get_inode(ino);
    in->i_mode = S_IFCHR | 0666;
    in->i_uid = 0;
    in->i_gid = 0;
    in->i_nlinks = 1;
    in->i_size = 0;
    in->i_time = 0;
    in->i_zone[0] = (uint16_t)((major << 8) | (minor & 0xff));
    return ino;
}

static int add_dir(int parent_ino, const char *name)
{
    int ino = mkdir_inode(parent_ino);
    add_dirent(parent_ino, name, ino);
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

static void *wrap_aout(const char *path, size_t *out_len)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0) die("open %s: %s", path, strerror(errno));
    struct stat st;
    fstat(fd, &st);
    size_t text = (size_t)st.st_size;
    size_t total = A_TXTOFF + text;
    uint8_t *buf = calloc(1, total);
    if (!buf) die("oom");
    struct a_out_header *h = (struct a_out_header *)buf;
    h->a_magic = ZMAGIC;
    h->a_text  = (uint32_t)text;
    h->a_data  = 0;
    h->a_bss   = 0x10000;
    h->a_syms  = 0;
    h->a_entry = 0;
    h->a_trsize = 0;
    h->a_drsize = 0;
    ssize_t n = read(fd, buf + A_TXTOFF, text);
    if (n != (ssize_t)text) die("short read on %s", path);
    close(fd);
    *out_len = total;
    return buf;
}

/* Strip path and extension: "/foo/bar.baz" → "bar" */
static const char *stem(const char *path)
{
    const char *base = basename((char *)path);
    static char buf[NAME_LEN + 1];
    strncpy(buf, base, NAME_LEN);
    buf[NAME_LEN] = 0;
    char *dot = strchr(buf, '.');
    if (dot) *dot = 0;
    return buf;
}

/* ------------------------------------------------------------------ */
int main(int argc, char **argv)
{
    if (argc < 2) die("usage: %s out.img [file.bin ...]", argv[0]);
    const char *out_path = argv[1];
    int n_files = argc - 2;
    char **file_paths = argv + 2;

    fs_size = (uint64_t)NZONES * BLOCK_SIZE;
    fs_img = calloc(1, fs_size);
    if (!fs_img) die("oom (%llu)", (unsigned long long)fs_size);

    sb = (struct minix_super *)BLOCK(1);
    sb->s_ninodes        = NINODES;
    sb->s_nzones         = NZONES;
    sb->s_imap_blocks    = IMAP_BLOCKS;
    sb->s_zmap_blocks    = ZMAP_BLOCKS;
    sb->s_firstdatazone  = FIRST_DATA_ZONE;
    sb->s_log_zone_size  = 0;
    sb->s_max_size       = 0x10081C00;
    sb->s_magic          = SUPER_MAGIC;

    set_bit(BLOCK(2), 0);
    set_bit(BLOCK(3), 0);

    int root_ino = mkdir_inode(0);
    if (root_ino != 1) die("root ino isn't 1?!");

    int bin_ino = add_dir(root_ino, "bin");
    int dev_ino = add_dir(root_ino, "dev");
    int etc_ino = add_dir(root_ino, "etc");
    int home_ino = add_dir(root_ino, "home");
    add_dir(home_ino, "fermihart");
    add_dir(root_ino, "tmp");

	add_file(etc_ino, "fstab", "/dev/hd1 / minix rw 0 0\n", 0644);
	add_file(etc_ino, "passwd", "root:x:0:0:root:/home/fermihart:/bin/shell\n", 0644);
	add_file(etc_ino, "issue",
		"Linux 0.01 modern root filesystem\n"
		"Try: ls -la, cat /etc/fstab, whoami, mount, df, ps aux\n", 0644);
	add_file(etc_ino, "motd",
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
		"Linus felt when he posted to comp.os.minix on that October morning:\n"
		"\n"
		"  I'm doing a (free) operating system (just a hobby, won't be\n"
		"  big and professional).\n"
		"\n"
		"He was wrong about the scale. But he was right about the spirit.\n"
		"\n"
		"This project exists to keep that spirit running. Not frozen. Not\n"
		"emulated behind a glass pane. Running. The original linux-0.01\n"
		"source is still here, still recognizable, still the heart of the\n"
		"machine. What we added is the thinnest possible bridge between\n"
		"that world and this one: a modern bootloader so the kernel can\n"
		"reach hardware, a toolchain that speaks 2026 C while respecting\n"
		"1991 conventions, and just enough runtime patches to make the\n"
		"thing boot without panicking on its own assumptions.\n"
		"\n"
		"The experience we tried to bring back alive is the one Linus\n"
		"described: you sit at a terminal, you type, the machine answers.\n"
		"There is no container orchestration between you and the process\n"
		"table. There is no init system with seventy stages. There is a\n"
		"kernel, a console, a shell, and you.\n"
		"\n"
		"Welcome to 1991. It still runs in 2026.\n", 0644);
	add_chr(dev_ino, "tty0", 4, 0);

    for (int i = 0; i < n_files; i++) {
        size_t len;
        void *buf = wrap_aout(file_paths[i], &len);
        int ino = mkfile_inode(buf, len);
        add_dirent(bin_ino, stem(file_paths[i]), ino);
        fprintf(stderr, "  added /bin/%-12s (%zu bytes, inode %d)\n",
                stem(file_paths[i]), len, ino);
        free(buf);
    }

    fprintf(stderr,
        "  minix v1 fs: %d inodes used, %d zones used, first data zone = %d\n",
        next_inode - 1, next_zone - FIRST_DATA_ZONE, FIRST_DATA_ZONE);

    uint64_t fs_sectors = fs_size / SECTOR_SIZE;
    uint64_t disk_sectors = fs_sectors + 1;
    uint64_t disk_size = disk_sectors * SECTOR_SIZE;

    uint64_t target_total = 977 * 5 * 17 * 512;
    if (disk_size < target_total) disk_size = target_total;

    uint8_t *disk = calloc(1, disk_size);
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
    p[0].start_sect= 1;
    p[0].nr_sects  = (uint32_t)(disk_sectors - 1);
    disk[510] = 0x55;
    disk[511] = 0xAA;

    memcpy(disk + SECTOR_SIZE, fs_img, fs_size);

    int fd = open(out_path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) die("open %s: %s", out_path, strerror(errno));
    ssize_t w = write(fd, disk, disk_size);
    if (w != (ssize_t)disk_size) die("short write");
    close(fd);
    free(disk);
    free(fs_img);

    fprintf(stderr, "  wrote %s  (%llu bytes, %llu sectors)\n",
            out_path, (unsigned long long)disk_size,
            (unsigned long long)disk_sectors);
    return 0;
}
