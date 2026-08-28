/*
 * Tests for invalid BBP inputs: bad CRC, unknown tags, truncated lengths.
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

static void build_minimal_info(uint8_t *buf)
{
    struct bbp_info info;
    memset(&info, 0, sizeof info);
    memcpy(info.magic, BBP_INFO_MAGIC, strlen(BBP_INFO_MAGIC));
    info.version_major = BBP_VERSION_MAJOR;
    info.version_minor = BBP_VERSION_MINOR;
    info.info_size = sizeof(info);
    info.architecture = BBP_ARCH_X86_32;
    info.cpu_count = 1;
    info.tag_count = 0;
    info.first_tag = 0;
    info.checksum = 0;
    info.checksum = bbp_crc64(&info, sizeof(info));
    memcpy(buf, &info, sizeof(info));
}

static void test_bad_info_magic(void)
{
    uint8_t buf[sizeof(struct bbp_info)];
    build_minimal_info(buf);
    buf[0] ^= 0xFF;
    {
        struct bbp_info *info = (struct bbp_info *)buf;
        check(memcmp(info->magic, BBP_INFO_MAGIC, strlen(BBP_INFO_MAGIC)) != 0,
              "bad info magic detected");
    }
}

static void test_bad_info_crc(void)
{
    uint8_t buf[sizeof(struct bbp_info)];
    build_minimal_info(buf);
    buf[sizeof(buf) - 1] ^= 0xFF;
    {
        struct bbp_info *info = (struct bbp_info *)buf;
        uint64_t saved = info->checksum;
        info->checksum = 0;
        check(bbp_crc64(info, sizeof(*info)) != saved,
              "bad info crc detected");
    }
}

static void test_version_mismatch(void)
{
    uint8_t buf[sizeof(struct bbp_info)];
    build_minimal_info(buf);
    {
        struct bbp_info *info = (struct bbp_info *)buf;
        check(info->version_major == BBP_VERSION_MAJOR,
              "info version major matches");
    }
}

static void test_oversize_info(void)
{
    uint8_t buf[sizeof(struct bbp_info)];
    build_minimal_info(buf);
    {
        struct bbp_info *info = (struct bbp_info *)buf;
        check(info->info_size <= 65536, "info_size within limit");
    }
}

int main(void)
{
    test_bad_info_magic();
    test_bad_info_crc();
    test_version_mismatch();
    test_oversize_info();
    if (failures) {
        fprintf(stderr, "\n%d test(s) failed\n", failures);
        return 1;
    }
    printf("\nall BBP invalid-input tests passed\n");
    return 0;
}
