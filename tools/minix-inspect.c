/*
 * minix-inspect.c — independent Minix v1 filesystem inspector.
 *
 * Reads the first partition of a raw disk image (after the MBR) and prints
 * a structural summary: superblock, bitmaps, inodes, directories and the
 * files they contain.
 *
 * Build:  gcc -O2 -Wall -o minix-inspect tools/minix-inspect.c
 * Run:    ./minix-inspect build/root.img
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>

#define BLOCK_SIZE      1024
#define SECTOR_SIZE     512
#define NAME_LEN        14
#define SUPER_MAGIC     0x137F

#ifndef S_IFREG
#define S_IFREG  0100000
#endif
#ifndef S_IFDIR
#define S_IFDIR  0040000
#endif
#ifndef S_IFCHR
#define S_IFCHR  0020000
#endif

struct minix_super {
    uint16_t s_ninodes;
    uint16_t s_nzones;
    uint16_t s_imap_blocks;
    uint16_t s_zmap_blocks;
    uint16_t s_firstdatazone;
    uint16_t s_log_zone_size;
    uint32_t s_max_size;
    uint16_t s_magic;
} __attribute__((packed));

struct minix_inode {
    uint16_t i_mode;
    uint16_t i_uid;
    uint32_t i_size;
    uint32_t i_time;
    uint8_t  i_gid;
    uint8_t  i_nlinks;
    uint16_t i_zone[9];
} __attribute__((packed));

struct minix_dirent {
    uint16_t inode;
    char     name[NAME_LEN];
} __attribute__((packed));

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

static uint8_t *image;
static size_t image_size;
static uint32_t part_start;

static uint16_t get_le16(const uint8_t *p)
{
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t get_le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint32_t get_le32p(const void *p) { return get_le32(p); }
static uint16_t get_le16p(const void *p) { return get_le16(p); }

static void die(const char *msg)
{
    fprintf(stderr, "minix-inspect: %s\n", msg);
    exit(1);
}

static uint8_t *block(unsigned n)
{
    size_t off = SECTOR_SIZE + (size_t)n * BLOCK_SIZE;
    if (off + BLOCK_SIZE > image_size) die("block out of range");
    return image + off;
}

static int test_bit(const uint8_t *bmap, int bit)
{
    return (bmap[bit >> 3] >> (bit & 7)) & 1;
}

static void dump_super(const struct minix_super *sb)
{
    printf("superblock:\n");
    printf("  s_ninodes       %u\n", get_le16p(&sb->s_ninodes));
    printf("  s_nzones        %u\n", get_le16p(&sb->s_nzones));
    printf("  s_imap_blocks   %u\n", get_le16p(&sb->s_imap_blocks));
    printf("  s_zmap_blocks   %u\n", get_le16p(&sb->s_zmap_blocks));
    printf("  s_firstdatazone %u\n", get_le16p(&sb->s_firstdatazone));
    printf("  s_log_zone_size %u\n", get_le16p(&sb->s_log_zone_size));
    printf("  s_max_size      %u\n", get_le32p(&sb->s_max_size));
    printf("  s_magic         0x%04X%s\n",
           get_le16p(&sb->s_magic),
           get_le16p(&sb->s_magic) == SUPER_MAGIC ? " (v1)" : " (BAD)");
}

static void dump_inode(int nr, const struct minix_inode *in)
{
    uint16_t mode = get_le16p(&in->i_mode);
    char type = '-';
    if ((mode & S_IFDIR) == S_IFDIR) type = 'd';
    else if ((mode & S_IFCHR) == S_IFCHR) type = 'c';
    else if ((mode & S_IFREG) == S_IFREG) type = '-';

    printf("inode %3d  %c%04o  uid %u  gid %u  nlink %u  size %u  time %u\n",
           nr, type, mode & 07777, get_le16p(&in->i_uid), in->i_gid,
           in->i_nlinks, get_le32p(&in->i_size), get_le32p(&in->i_time));

    printf("  zones:");
    for (int i = 0; i < 9; i++)
        printf(" %u", get_le16p(&in->i_zone[i]));
    printf("\n");
}

static void dump_file(const struct minix_inode *in)
{
    uint32_t size = get_le32p(&in->i_size);
    uint32_t got = 0;
    for (int i = 0; i < 7 && got < size; i++) {
        uint16_t z = get_le16p(&in->i_zone[i]);
        if (!z) continue;
        uint32_t chunk = size - got;
        if (chunk > BLOCK_SIZE) chunk = BLOCK_SIZE;
        fwrite(block(z), 1, chunk, stdout);
        got += chunk;
    }
    if (got < size) {
        uint16_t ind = get_le16p(&in->i_zone[7]);
        if (ind) {
            const uint8_t *zones = block(ind);
            for (size_t i = 0; i < BLOCK_SIZE / 2 && got < size; i++) {
                uint16_t z = get_le16(zones + i * 2);
                if (!z) continue;
                uint32_t chunk = size - got;
                if (chunk > BLOCK_SIZE) chunk = BLOCK_SIZE;
                fwrite(block(z), 1, chunk, stdout);
                got += chunk;
            }
        }
    }
    if (got < size) {
        uint16_t dind = get_le16p(&in->i_zone[8]);
        if (dind) {
            const uint8_t *dtable = block(dind);
            for (size_t d = 0; d < BLOCK_SIZE / 2 && got < size; d++) {
                uint16_t ind = get_le16(dtable + d * 2);
                if (!ind) continue;
                const uint8_t *zones = block(ind);
                for (size_t i = 0; i < BLOCK_SIZE / 2 && got < size; i++) {
                    uint16_t z = get_le16(zones + i * 2);
                    if (!z) continue;
                    uint32_t chunk = size - got;
                    if (chunk > BLOCK_SIZE) chunk = BLOCK_SIZE;
                    fwrite(block(z), 1, chunk, stdout);
                    got += chunk;
                }
            }
        }
    }
}

static void dump_dir(const struct minix_inode *in)
{
    uint32_t size = get_le32p(&in->i_size);
    uint32_t got = 0;
    for (int pass = 0; pass < 9 && got < size; pass++) {
        uint16_t z;
        const uint8_t *data;
        if (pass < 7) {
            z = get_le16p(&in->i_zone[pass]);
            if (!z) continue;
            data = block(z);
        } else if (pass == 7) {
            /* single indirect */
            continue;
        } else {
            /* double indirect */
            continue;
        }
        for (size_t i = 0; i < BLOCK_SIZE / sizeof(struct minix_dirent) && got < size; i++) {
            const struct minix_dirent *de = (const struct minix_dirent *)data + i;
            uint16_t ino = get_le16p(&de->inode);
            if (!ino) continue;
            char name[NAME_LEN + 1];
            memcpy(name, de->name, NAME_LEN);
            name[NAME_LEN] = 0;
            printf("  %-14s -> inode %u\n", name, ino);
            got += sizeof(struct minix_dirent);
        }
    }
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s <disk-image>\n", argv[0]);
        return 1;
    }

    int fd = open(argv[1], O_RDONLY);
    if (fd < 0) { perror("open"); return 1; }
    off_t end = lseek(fd, 0, SEEK_END);
    if (end < 0) { perror("lseek"); return 1; }
    if (end > (off_t)(1 << 30)) die("image too large");
    image_size = (size_t)end;
    image = malloc(image_size);
    if (!image) die("oom");
    lseek(fd, 0, SEEK_SET);
    if (read(fd, image, image_size) != (ssize_t)image_size) die("short read");
    close(fd);

    if (image_size < SECTOR_SIZE) die("image too small for MBR");
    struct mbr_part *ptbl = (struct mbr_part *)(image + 0x1BE);
    part_start = get_le32p(&ptbl[0].start_sect) / 2; /* sectors -> blocks */
    if (part_start * BLOCK_SIZE + BLOCK_SIZE > image_size)
        die("partition start out of range");

    printf("MBR partition 0 start_sect=%u (block %u)\n",
           get_le32p(&ptbl[0].start_sect), part_start);

    struct minix_super *sb = (struct minix_super *)block(1);
    dump_super(sb);

    uint16_t ninodes = get_le16p(&sb->s_ninodes);
    uint16_t nzones = get_le16p(&sb->s_nzones);
    uint16_t imap_blocks = get_le16p(&sb->s_imap_blocks);
    uint16_t zmap_blocks = get_le16p(&sb->s_zmap_blocks);
    uint16_t firstdatazone = get_le16p(&sb->s_firstdatazone);

    printf("\ninodes: %u, zones: %u, first data zone: %u\n", ninodes, nzones, firstdatazone);

    printf("\nused inodes:");
    int used_inodes = 0;
    for (int i = 1; i <= ninodes; i++) {
        if (test_bit(block(2), i)) {
            printf(" %d", i);
            used_inodes++;
        }
    }
    printf(" (total %d)\n", used_inodes);

    printf("used zones:");
    int used_zones = 0;
    for (int i = firstdatazone; i < nzones; i++) {
        int bit = i - (firstdatazone - 1);
        if (test_bit(block(2 + imap_blocks), bit)) {
            printf(" %d", i);
            used_zones++;
        }
    }
    printf(" (total %d)\n", used_zones);

    int inode_blocks = (ninodes + (BLOCK_SIZE / 32) - 1) / (BLOCK_SIZE / 32);
    printf("\ninode table (%d blocks):\n", inode_blocks);
    for (int i = 1; i <= ninodes; i++) {
        int blk = 2 + imap_blocks + zmap_blocks + (i - 1) / (BLOCK_SIZE / 32);
        int off = (i - 1) % (BLOCK_SIZE / 32);
        const struct minix_inode *in = (const struct minix_inode *)block(blk) + off;
        if (get_le16p(&in->i_mode) == 0) continue;
        dump_inode(i, in);
        uint16_t mode = get_le16p(&in->i_mode);
        if ((mode & S_IFDIR) == S_IFDIR)
            dump_dir(in);
    }

    printf("\nregular file contents:\n");
    for (int i = 1; i <= ninodes; i++) {
        int blk = 2 + imap_blocks + zmap_blocks + (i - 1) / (BLOCK_SIZE / 32);
        int off = (i - 1) % (BLOCK_SIZE / 32);
        const struct minix_inode *in = (const struct minix_inode *)block(blk) + off;
        uint16_t mode = get_le16p(&in->i_mode);
        if ((mode & S_IFREG) != S_IFREG || get_le32p(&in->i_size) == 0) continue;
        printf("--- inode %d (%u bytes) ---\n", i, get_le32p(&in->i_size));
        dump_file(in);
        printf("\n");
    }

    return 0;
}
