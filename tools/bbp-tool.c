/*
 * bbp-tool.c - reference encoder/decoder for the Bear Boot Protocol.
 *
 * Usage:
 *   bbp-tool encode OUTPUT_FILE
 *   bbp-tool decode INPUT_FILE
 */

#include <bbp/bbp.h>
#include <bbp/bbp_crc64.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void die(const char *msg)
{
    perror(msg);
    exit(1);
}

static void write_full(FILE *f, const void *buf, size_t size)
{
    if (fwrite(buf, 1, size, f) != size)
        die("fwrite");
}

static uint64_t tag_crc(const struct bbp_tag_header *hdr)
{
    uint64_t saved = hdr->checksum;
    ((struct bbp_tag_header *)hdr)->checksum = 0;
    uint64_t c = bbp_crc64(hdr, hdr->tag_size);
    ((struct bbp_tag_header *)hdr)->checksum = saved;
    return c;
}

static void encode(const char *path)
{
    struct bbp_header hdr;
    struct bbp_info info;
    struct bbp_tag_cmdline cmdline;
    struct bbp_tag_hhdm hhdm;
    size_t off_cmdline, off_hhdm;
    FILE *f = fopen(path, "wb");
    if (!f)
        die(path);

    memset(&hdr, 0, sizeof hdr);
    memcpy(hdr.magic, BBP_HEADER_MAGIC, strlen(BBP_HEADER_MAGIC));
    hdr.version_major = BBP_VERSION_MAJOR;
    hdr.version_minor = BBP_VERSION_MINOR;
    hdr.header_size = sizeof(hdr);
    memcpy(hdr.kernel_name, "linux01-ref", 11);
    hdr.checksum = bbp_crc64(&hdr, sizeof(hdr));
    write_full(f, &hdr, sizeof(hdr));

    memset(&info, 0, sizeof info);
    memcpy(info.magic, BBP_INFO_MAGIC, strlen(BBP_INFO_MAGIC));
    info.version_major = BBP_VERSION_MAJOR;
    info.version_minor = BBP_VERSION_MINOR;
    memcpy(info.bootloader_name, "bbp-tool", 8);
    memcpy(info.bootloader_version, "ref-1", 5);
    info.architecture = BBP_ARCH_X86_32;
    info.cpu_count = 1;
    info.tag_count = 2;
    info.first_tag = sizeof(hdr) + sizeof(info);

    write_full(f, &info, sizeof(info));

    /* first tag: CMDLINE */
    off_cmdline = ftell(f);
    memset(&cmdline, 0, sizeof cmdline);
    cmdline.header.tag_id = BBP_TAG_CMDLINE;
    cmdline.header.tag_size = sizeof(cmdline);
    cmdline.header.tag_version = 0;
    cmdline.header.flags = BBP_TF_NONE;
    cmdline.header.next_tag = 0; /* filled later */
    write_full(f, &cmdline, sizeof(cmdline));

    /* second tag: HHDM */
    off_hhdm = ftell(f);
    memset(&hhdm, 0, sizeof hhdm);
    hhdm.header.tag_id = BBP_TAG_HHDM;
    hhdm.header.tag_size = sizeof(hhdm);
    hhdm.header.tag_version = 0;
    hhdm.header.flags = BBP_TF_NONE;
    hhdm.header.next_tag = 0;
    hhdm.offset = 0;
    write_full(f, &hhdm, sizeof(hhdm));

    info.info_size = (uint32_t)ftell(f);

    /* fixup next_tag in cmdline */
    fseek(f, (long)off_cmdline + offsetof(struct bbp_tag_header, next_tag), SEEK_SET);
    {
        bbp_phys_t next = sizeof(hdr) + sizeof(info) + sizeof(cmdline);
        write_full(f, &next, sizeof(next));
    }

    /* fixup checksums */
    fseek(f, (long)off_cmdline + offsetof(struct bbp_tag_header, checksum), SEEK_SET);
    {
        uint64_t crc = tag_crc(&cmdline.header);
        write_full(f, &crc, sizeof(crc));
    }
    fseek(f, (long)off_hhdm + offsetof(struct bbp_tag_header, checksum), SEEK_SET);
    {
        uint64_t crc = tag_crc(&hhdm.header);
        write_full(f, &crc, sizeof(crc));
    }

    fseek(f, (long)(sizeof(hdr) + offsetof(struct bbp_info, info_size)), SEEK_SET);
    write_full(f, &info.info_size, sizeof(info.info_size));

    fseek(f, (long)(sizeof(hdr) + offsetof(struct bbp_info, checksum)), SEEK_SET);
    {
        uint64_t crc = bbp_crc64(&info, sizeof(info));
        write_full(f, &crc, sizeof(crc));
    }

    fclose(f);
    printf("wrote reference BBP to %s\n", path);
}

static int decode(const char *path)
{
    struct bbp_header hdr;
    struct bbp_info info;
    FILE *f = fopen(path, "rb");
    uint64_t ck;
    if (!f)
        die(path);
    if (fread(&hdr, 1, sizeof(hdr), f) != sizeof(hdr))
        die("short read header");
    if (memcmp(hdr.magic, BBP_HEADER_MAGIC, strlen(BBP_HEADER_MAGIC)) != 0) {
        fprintf(stderr, "bad header magic\n");
        return 1;
    }
    ck = hdr.checksum;
    hdr.checksum = 0;
    if (bbp_crc64(&hdr, sizeof(hdr)) != ck) {
        fprintf(stderr, "header checksum mismatch\n");
        return 1;
    }
    if (fread(&info, 1, sizeof(info), f) != sizeof(info))
        die("short read info");
    if (memcmp(info.magic, BBP_INFO_MAGIC, strlen(BBP_INFO_MAGIC)) != 0) {
        fprintf(stderr, "bad info magic\n");
        return 1;
    }
    ck = info.checksum;
    info.checksum = 0;
    if (bbp_crc64(&info, sizeof(info)) != ck) {
        fprintf(stderr, "info checksum mismatch\n");
        return 1;
    }
    printf("BBP info: version=%u.%u arch=%u cpus=%u tags=%u\n",
           info.version_major, info.version_minor,
           info.architecture, info.cpu_count, info.tag_count);
    fclose(f);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s encode|decode FILE\n", argv[0]);
        return 2;
    }
    if (!strcmp(argv[1], "encode")) {
        encode(argv[2]);
        return 0;
    }
    if (!strcmp(argv[1], "decode")) {
        return decode(argv[2]);
    }
    fprintf(stderr, "unknown command: %s\n", argv[1]);
    return 2;
}
