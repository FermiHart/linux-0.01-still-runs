/*
 * Author: F E R M I INFINITY H A R T <contact@fermihart.com>
 * SPDX-License-Identifier: Unlicense
 */

/*
 * Golden-vector test for BBP reference decoder.
 * The vector is produced by `make bbp-golden-vectors` via tools/bbp-tool.
 */

#include <stdio.h>
#include <string.h>

#include "../../bbp/include/bbp/bbp.h"
#include "../../bbp/include/bbp/bbp_crc64.h"

static int failures = 0;

static void check(int condition, const char *name)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", name);
        failures++;
    } else {
        printf("ok  %s\n", name);
    }
}

int main(int argc, char **argv)
{
    const char *path = (argc > 1) ? argv[1] : "tests/bemu/golden/bbp-minimal.bin";
    struct bbp_header hdr;
    struct bbp_info info;
    uint64_t ck;
    FILE *f = fopen(path, "rb");
    if (!f) {
        perror(path);
        return 1;
    }
    if (fread(&hdr, 1, sizeof(hdr), f) != sizeof(hdr)) {
        fprintf(stderr, "short read header\n");
        return 1;
    }
    check(memcmp(hdr.magic, BBP_HEADER_MAGIC, strlen(BBP_HEADER_MAGIC)) == 0,
          "golden header magic");
    check(hdr.version_major == BBP_VERSION_MAJOR, "golden header version major");
    ck = hdr.checksum;
    hdr.checksum = 0;
    check(bbp_crc64(&hdr, sizeof(hdr)) == ck, "golden header checksum");

    if (fread(&info, 1, sizeof(info), f) != sizeof(info)) {
        fprintf(stderr, "short read info\n");
        return 1;
    }
    check(memcmp(info.magic, BBP_INFO_MAGIC, strlen(BBP_INFO_MAGIC)) == 0,
          "golden info magic");
    check(info.architecture == BBP_ARCH_X86_32, "golden info architecture");
    check(info.cpu_count == 1, "golden info cpu count");
    check(info.tag_count == 2, "golden info tag count");
    ck = info.checksum;
    info.checksum = 0;
    check(bbp_crc64(&info, sizeof(info)) == ck, "golden info checksum");

    fclose(f);
    if (failures) {
        fprintf(stderr, "\n%d check(s) failed\n", failures);
        return 1;
    }
    printf("\ngolden BBP vector decoded successfully\n");
    return 0;
}
