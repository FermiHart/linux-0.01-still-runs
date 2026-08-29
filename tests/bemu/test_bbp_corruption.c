/*
 * Author: F E R M I INFINITY H A R T <contact@fermihart.com>
 * SPDX-License-Identifier: Unlicense
 */

/* Exercise BBP corruption through Linux 0.01's exact production consumer. */

#define _GNU_SOURCE
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>

#include <bbp/bbp.h>
#include <bbp/bbp_crc64.h>
#include "../../bbp/bbp_build.h"
#include "../../bbp/linux01_bbp.h"
#include "../../bbp/linux01_handoff.h"

#define HANDOFF_SIZE (BBP_L01_HANDOFF_END - BBP_L01_HANDOFF_PHYS)

struct fixture {
    struct bbp_info *info;
    struct bbp_tag_hhdm *hhdm;
    struct bbp_tag_memory_map *mmap;
    struct bbp_memory_entry *memory;
    struct bbp_tag_kernel_address *kernel;
    struct bbp_tag_cmdline *cmdline;
    struct bbp_tag_hypervisor *hypervisor;
    char *command;
};

static struct fixture f;
static uint8_t pristine[HANDOFF_SIZE];
static char printk_log[2048];
static size_t printk_len;
static int failures;
static int case_precondition;

int printk(const char *format, ...)
{
    va_list args;
    int written;

    if (printk_len >= sizeof(printk_log))
        return 0;
    va_start(args, format);
    written = vsnprintf(printk_log + printk_len,
                        sizeof(printk_log) - printk_len, format, args);
    va_end(args);
    if (written > 0) {
        size_t available = sizeof(printk_log) - printk_len;
        printk_len += (size_t)written < available ? (size_t)written : available - 1;
    }
    return written;
}

static void check(int condition, const char *name)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", name);
        failures++;
    } else {
        printf("ok  %s\n", name);
    }
}

static void seal_info(void)
{
    f.info->checksum = 0;
    f.info->checksum = bbp_crc64(f.info, sizeof(*f.info));
}

static void seal_tag(struct bbp_tag_header *tag)
{
    tag->checksum = 0;
    tag->checksum = bbp_crc64(tag, tag->tag_size);
}

static int build_fixture(const char *command)
{
    struct bbp_builder builder;
    uint8_t *arena = (uint8_t *)(f.info + 1);
    size_t capacity = HANDOFF_SIZE - sizeof(*f.info);
    bbp_phys_t command_phys;
    uint32_t command_len;

    memset(f.info, 0, HANDOFF_SIZE);
    bbp_builder_init(&builder, arena,
                     BBP_L01_HANDOFF_PHYS + sizeof(*f.info), capacity);
    command_phys = bbp_arena_strdup(&builder, command, &command_len);
    f.command = (char *)(uintptr_t)command_phys;

    f.hhdm = bbp_alloc_tag(&builder, BBP_TAG_HHDM, 1, sizeof(*f.hhdm));
    f.mmap = bbp_alloc_tag(&builder, BBP_TAG_MEMORY_MAP, 1,
                           sizeof(*f.mmap) + 3 * sizeof(*f.memory));
    f.kernel = bbp_alloc_tag(&builder, BBP_TAG_KERNEL_ADDRESS, 1,
                             sizeof(*f.kernel));
    f.cmdline = bbp_alloc_tag(&builder, BBP_TAG_CMDLINE, 1,
                              sizeof(*f.cmdline));
    f.hypervisor = bbp_alloc_tag(&builder, BBP_TAG_HYPERVISOR, 1,
                                 sizeof(*f.hypervisor));
    if (!command_phys || !f.hhdm || !f.mmap || !f.kernel || !f.cmdline ||
        !f.hypervisor || builder.overflow)
        return -1;

    f.hhdm->offset = 0;
    f.mmap->entry_count = 3;
    f.mmap->entry_size = sizeof(*f.memory);
    f.memory = (struct bbp_memory_entry *)(f.mmap + 1);
    f.memory[0].base = 0;
    f.memory[0].length = 0xA0000;
    f.memory[0].type = BBP_MEM_USABLE;
    f.memory[0].attributes = BBP_MEM_ATTR_READABLE | BBP_MEM_ATTR_WRITABLE |
                             BBP_MEM_ATTR_CACHED;
    f.memory[1].base = 0xA0000;
    f.memory[1].length = 0x60000;
    f.memory[1].type = BBP_MEM_RESERVED;
    f.memory[1].attributes = BBP_MEM_ATTR_READABLE;
    f.memory[2].base = 0x100000;
    f.memory[2].length = 0x700000;
    f.memory[2].type = BBP_MEM_USABLE;
    f.memory[2].attributes = BBP_MEM_ATTR_READABLE | BBP_MEM_ATTR_WRITABLE |
                             BBP_MEM_ATTR_CACHED;
    f.kernel->physical_base = 0;
    f.kernel->virtual_base = 0;
    f.cmdline->string = command_phys;
    f.cmdline->length = command_len;
    f.cmdline->string_crc = bbp_crc64(command, command_len);
    f.hypervisor->present = 1;
    memcpy(f.hypervisor->vendor, "bEMU", 4);

    memcpy(f.info->bootloader_name, "bEMU-NANO", 9);
    memcpy(f.info->bootloader_version, "linux01-1", 9);
    f.info->architecture = BBP_ARCH_X86_32;
    f.info->cpu_count = 1;
    if (!bbp_builder_finalize(&builder, f.info, BBP_L01_HANDOFF_PHYS))
        return -1;
    memcpy(pristine, f.info, HANDOFF_SIZE);
    return 0;
}

static void restore_fixture(void)
{
    memcpy(f.info, pristine, HANDOFF_SIZE);
    printk_len = 0;
    printk_log[0] = '\0';
    case_precondition = 1;
}

static const char *expected_status_text(bbp_status_t status)
{
    switch (status) {
    case BBP_OK:               return "ok";
    case BBP_ERR_MAGIC:        return "bad magic (not BEAR_INFO/BEAR_BOOT)";
    case BBP_ERR_VERSION:      return "incompatible protocol major version";
    case BBP_ERR_CHECKSUM:     return "info CRC64 mismatch";
    case BBP_ERR_SIZE:         return "implausible info_size";
    case BBP_ERR_TAG_CHECKSUM: return "tag CRC64 mismatch";
    default:                   return NULL;
    }
}

static void run_case(const char *name, bbp_status_t expected,
                     const char *experience, void (*mutate)(void))
{
    bbp_status_t status;
    const char *status_text = expected_status_text(expected);
    char expected_log[160];
    int valid;

    restore_fixture();
    if (mutate)
        mutate();
    status = bbp_linux01_init();
    if (expected == BBP_OK) {
        snprintf(expected_log, sizeof(expected_log),
                 "[bbp] bEMU handoff: ok, 5 tags, %s\n",
                 strcmp(experience, "1991") == 0 ? BBP_L01_1991_CMDLINE :
                                                   BBP_L01_ALIVE_CMDLINE);
    } else {
        snprintf(expected_log, sizeof(expected_log),
                 "[bbp] bEMU handoff: %s (non-fatal, kernel continues)\n",
                 status_text);
    }
    valid = case_precondition && status_text && status == expected &&
            strcmp(printk_log, expected_log) == 0;
    if (expected == BBP_OK) {
        valid = valid && bbp_linux01_boot_ctx() != NULL &&
                bbp_linux01_experience() != NULL &&
                strcmp(bbp_linux01_experience(), experience) == 0;
    } else {
        valid = valid && bbp_linux01_boot_ctx() == NULL &&
                bbp_linux01_experience() == NULL;
    }
    check(valid, name);
}

static void bad_info_magic(void) { f.info->magic[0] ^= 0x80; }
static void bad_info_version(void)
{
    f.info->version_major++;
    seal_info();
}
static void bad_info_crc(void) { f.info->checksum ^= 1; }
static void short_info(void)
{
    f.info->info_size = sizeof(*f.info) - 1;
    seal_info();
}
static void oversized_linux01_info(void)
{
    f.info->info_size = HANDOFF_SIZE + 1;
    seal_info();
}
static void tag_outside_window(void)
{
    f.info->first_tag = BBP_L01_HANDOFF_END;
    seal_info();
}
static void tag_unaligned(void)
{
    f.info->first_tag++;
    seal_info();
}
static void tag_exceeds_window(void)
{
    f.hhdm->header.tag_size =
        (uint32_t)(BBP_L01_HANDOFF_END - (uintptr_t)f.hhdm + 1);
}
static void bad_tag_version(void)
{
    f.hhdm->header.tag_version++;
    seal_tag(&f.hhdm->header);
}
static void bad_tag_crc(void) { f.hhdm->offset = 1; }
static void interior_next_tag(void)
{
    f.hhdm->header.next_tag = (bbp_phys_t)(uintptr_t)f.mmap +
                              sizeof(struct bbp_tag_header);
    seal_tag(&f.hhdm->header);
}
static void overlapping_tag_extent(void)
{
    struct bbp_kctx parsed;

    f.kernel->header.tag_size =
        (uint32_t)((uintptr_t)f.cmdline + sizeof(struct bbp_tag_header) -
                   (uintptr_t)f.kernel);
    seal_tag(&f.kernel->header);
    case_precondition = bbp_init_win(&parsed, f.info, 0,
                                     BBP_L01_HANDOFF_PHYS,
                                     BBP_L01_HANDOFF_END) == BBP_OK;
}
static void cyclic_chain(void)
{
    f.hypervisor->header.next_tag = f.info->first_tag;
    seal_tag(&f.hypervisor->header);
}
static void count_chain_mismatch(void)
{
    f.info->tag_count--;
    seal_info();
}
static void missing_kernel_tag(void)
{
    f.kernel->header.tag_id = BBP_TAG_METRICS;
    seal_tag(&f.kernel->header);
}
static void duplicate_hhdm(void)
{
    f.kernel->header.tag_id = BBP_TAG_HHDM;
    seal_tag(&f.kernel->header);
}
static void wrong_architecture(void)
{
    f.info->architecture = BBP_ARCH_X86_64;
    seal_info();
}
static void wrong_producer(void)
{
    f.info->bootloader_name[0] = 'x';
    seal_info();
}
static void redirected_hhdm(void)
{
    f.hhdm->offset = 0x1000;
    seal_tag(&f.hhdm->header);
}
static void wrong_memory_geometry(void)
{
    f.memory[2].length--;
    seal_tag(&f.mmap->header);
}
static void wrong_kernel_address(void)
{
    f.kernel->physical_base = 1;
    seal_tag(&f.kernel->header);
}
static void absent_hypervisor(void)
{
    f.hypervisor->present = 0;
    seal_tag(&f.hypervisor->header);
}
static void corrupt_command_blob(void) { f.command[0] ^= 1; }
static void unsupported_command(void)
{
    f.command[0] = 'x';
    f.cmdline->string_crc = bbp_crc64(f.command, f.cmdline->length);
    seal_tag(&f.cmdline->header);
}

int main(void)
{
    void *mapping = mmap((void *)(uintptr_t)BBP_L01_HANDOFF_PHYS, HANDOFF_SIZE,
                         PROT_READ | PROT_WRITE,
                         MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE,
                         -1, 0);
    if (mapping == MAP_FAILED) {
        perror("mmap BBP handoff window");
        return 1;
    }
    if ((uintptr_t)mapping != BBP_L01_HANDOFF_PHYS) {
        fprintf(stderr, "FAIL: BBP handoff mapped at wrong address\n");
        munmap(mapping, HANDOFF_SIZE);
        return 1;
    }
    f.info = mapping;
    if (build_fixture(BBP_L01_ALIVE_CMDLINE) < 0) {
        fprintf(stderr, "FAIL: could not build canonical BBP fixture\n");
        munmap(mapping, HANDOFF_SIZE);
        return 1;
    }

    run_case("production consumer accepts canonical alive handoff",
             BBP_OK, "alive", NULL);
    run_case("production consumer rejects info magic corruption",
             BBP_ERR_MAGIC, NULL, bad_info_magic);
    run_case("production consumer rejects incompatible info version",
             BBP_ERR_VERSION, NULL, bad_info_version);
    run_case("production consumer rejects info CRC corruption",
             BBP_ERR_CHECKSUM, NULL, bad_info_crc);
    run_case("production consumer rejects truncated info size",
             BBP_ERR_SIZE, NULL, short_info);
    run_case("Linux 0.01 rejects info beyond its handoff window",
             BBP_ERR_SIZE, NULL, oversized_linux01_info);
    run_case("production consumer rejects tag outside walk window",
             BBP_ERR_SIZE, NULL, tag_outside_window);
    run_case("production consumer rejects unaligned tag pointer",
             BBP_ERR_SIZE, NULL, tag_unaligned);
    run_case("production consumer rejects tag extending beyond window",
             BBP_ERR_SIZE, NULL, tag_exceeds_window);
    run_case("production consumer rejects incompatible tag version",
             BBP_ERR_VERSION, NULL, bad_tag_version);
    run_case("production consumer rejects tag CRC corruption",
             BBP_ERR_TAG_CHECKSUM, NULL, bad_tag_crc);
    run_case("production consumer rejects next_tag into tag body",
             BBP_ERR_SIZE, NULL, interior_next_tag);
    run_case("Linux 0.01 rejects a structurally valid overlapping tag extent",
             BBP_ERR_SIZE, NULL, overlapping_tag_extent);
    run_case("production consumer bounds a cyclic tag chain",
             BBP_ERR_SIZE, NULL, cyclic_chain);
    run_case("production consumer rejects count and chain mismatch",
             BBP_ERR_SIZE, NULL, count_chain_mismatch);
    run_case("Linux 0.01 rejects a missing required tag",
             BBP_ERR_SIZE, NULL, missing_kernel_tag);
    run_case("production parser rejects duplicate HHDM tags",
             BBP_ERR_SIZE, NULL, duplicate_hhdm);
    run_case("Linux 0.01 rejects wrong architecture",
             BBP_ERR_SIZE, NULL, wrong_architecture);
    run_case("Linux 0.01 rejects wrong producer identity",
             BBP_ERR_SIZE, NULL, wrong_producer);
    run_case("production parser rejects redirected bounded HHDM",
             BBP_ERR_SIZE, NULL, redirected_hhdm);
    run_case("Linux 0.01 rejects wrong memory geometry",
             BBP_ERR_SIZE, NULL, wrong_memory_geometry);
    run_case("Linux 0.01 rejects wrong kernel address",
             BBP_ERR_SIZE, NULL, wrong_kernel_address);
    run_case("Linux 0.01 rejects missing hypervisor evidence",
             BBP_ERR_SIZE, NULL, absent_hypervisor);
    run_case("production consumer rejects command blob CRC corruption",
             BBP_ERR_TAG_CHECKSUM, NULL, corrupt_command_blob);
    run_case("Linux 0.01 rejects CRC-valid unsupported command",
             BBP_ERR_SIZE, NULL, unsupported_command);

    if (build_fixture(BBP_L01_1991_CMDLINE) < 0) {
        fprintf(stderr, "FAIL: could not build 1991 BBP fixture\n");
        failures++;
    } else {
        run_case("production consumer accepts canonical 1991 handoff",
                 BBP_OK, "1991", NULL);
    }
    munmap(mapping, HANDOFF_SIZE);
    if (failures) {
        fprintf(stderr, "\n%d BBP corruption test(s) failed\n", failures);
        return 1;
    }
    printf("\nall production BBP corruption tests passed\n");
    return 0;
}
