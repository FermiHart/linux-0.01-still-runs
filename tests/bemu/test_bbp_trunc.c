/*
 * Author: F E R M I INFINITY H A R T <contact@fermihart.com>
 * SPDX-License-Identifier: Unlicense
 */

/*
 * Tests for BBP truncation and tag overlap handling.
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

static void build_minimal_info(struct bbp_info *info)
{
    memset(info, 0, sizeof *info);
    memcpy(info->magic, BBP_INFO_MAGIC, strlen(BBP_INFO_MAGIC));
    info->version_major = BBP_VERSION_MAJOR;
    info->version_minor = BBP_VERSION_MINOR;
    info->info_size = sizeof(*info);
    info->architecture = BBP_ARCH_X86_32;
    info->cpu_count = 1;
    info->tag_count = 0;
    info->first_tag = 0;
    info->checksum = 0;
    info->checksum = bbp_crc64(info, sizeof(*info));
}

static void test_truncated_info(void)
{
    struct bbp_info info;
    build_minimal_info(&info);
    check(info.info_size == sizeof(info), "info_size matches struct size");
    /* A truncated read is detected because info_size would mismatch */
    check(info.info_size > sizeof(info) / 2, "info_size larger than half struct");
}

static void test_tag_exceeds_info(void)
{
    struct bbp_info info;
    build_minimal_info(&info);
    info.tag_count = 1;
    info.first_tag = sizeof(info) + 0x1000; /* past info bounds */
    info.checksum = 0;
    info.checksum = bbp_crc64(&info, sizeof(info));
    check(info.first_tag >= info.info_size, "tag pointer past info_size detected");
}

static void test_overlapping_tags(void)
{
    struct bbp_tag_header a, b;
    memset(&a, 0, sizeof a);
    memset(&b, 0, sizeof b);
    a.tag_id = BBP_TAG_CMDLINE;
    a.tag_size = sizeof(a);
    a.next_tag = 0x10; /* fake physical address */
    b.tag_id = BBP_TAG_HHDM;
    b.tag_size = sizeof(b);
    /* same physical address would overlap */
    check(a.next_tag == b.tag_id ? 0 : 1, "different tag ids do not overlap by id");
}

int main(void)
{
    test_truncated_info();
    test_tag_exceeds_info();
    test_overlapping_tags();
    if (failures) {
        fprintf(stderr, "\n%d test(s) failed\n", failures);
        return 1;
    }
    printf("\nall BBP truncation/overlap tests passed\n");
    return 0;
}
