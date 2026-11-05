/*
 * linux01_bbp.c — kernel glue for the Bear Boot Protocol on linux-0.01.
 *   Author: F E R M I ∞ H A R T <contact@fermihart.com>
 *   SPDX-License-Identifier: BSD-3-Clause
 *
 * This is the TU that turns the freestanding port into a real linux-0.01
 * subsystem. It does three things:
 *
 *   1. Finds bEMU's BBP handoff in the reserved PC legacy-memory hole.
 *   2. Validates its CRC-checksummed info and tag chain as untrusted input.
 *   3. Requires the machine identity and root-disk contract this port boots.
 *
 * The kernel is IDENTITY-mapped (pg_dir = 0, first 8 MiB), so HHDM offset is 0
 * and the handoff is SPEC §10.1(a). The call is additive + non-fatal.
 *
 * Build note: linux-0.01 is -nostdinc -m32 gnu89. The BBP core headers pull
 * <stdint.h>/<stddef.h>, satisfied by the vendored bbp/compat shims on the
 * include path (-Ibbp/compat in the kernel Makefile's BBP_CFLAGS).
 */
#include <bbp/bbp.h>
#include "bbp_kernel.h"
#include "linux01_bbp.h"
#include "linux01_handoff.h"

/* ===================================================================== *
 *  linux-0.01 kernel symbols we bind to. Declared here (not via the 1991
 *  headers) to keep this TU compilable both in-tree and for review. The
 *  signatures match kernel/printk.c and kernel/panic.c in linux-0.01-modern.
 * ===================================================================== */
extern int  printk(const char *fmt, ...);
static struct bbp_kctx l01_boot_ctx;
static int             l01_boot_ctx_valid = 0;
static const char     *l01_experience = (const char *)0;
static const char     *l01_command = BBP_L01_ALIVE_CMDLINE;

static int bytes_equal(const void *left, const void *right, unsigned length)
{
    const unsigned char *a = left;
    const unsigned char *b = right;
    unsigned i;
    for (i = 0; i < length; i++)
        if (a[i] != b[i])
            return 0;
    return 1;
}

bbp_status_t bbp_linux01_init(void)
{
    const struct bbp_info *info =
        (const struct bbp_info *)BBP_L01_HANDOFF_PHYS;
    const struct bbp_tag_hhdm *hhdm;
    const struct bbp_tag_memory_map *mmap;
    const struct bbp_memory_entry *memory;
    const struct bbp_tag_kernel_address *kernel;
    const struct bbp_tag_cmdline *cmdline;
    const struct bbp_tag_hypervisor *hypervisor;
    const char *command;
    bbp_status_t st;

    l01_boot_ctx_valid = 0;
    l01_experience = (const char *)0;
    l01_command = BBP_L01_ALIVE_CMDLINE;
    st = bbp_init_win(&l01_boot_ctx, info, 0, BBP_L01_HANDOFF_PHYS,
                      BBP_L01_HANDOFF_END);
    if (st != BBP_OK)
        goto out;
    hhdm = (const struct bbp_tag_hhdm *)
        bbp_find_tag(&l01_boot_ctx, BBP_TAG_HHDM);
    mmap = (const struct bbp_tag_memory_map *)
        bbp_find_tag(&l01_boot_ctx, BBP_TAG_MEMORY_MAP);
    kernel = (const struct bbp_tag_kernel_address *)
        bbp_find_tag(&l01_boot_ctx, BBP_TAG_KERNEL_ADDRESS);
    if (info->info_size > BBP_L01_HANDOFF_END - BBP_L01_HANDOFF_PHYS ||
        info->architecture != BBP_ARCH_X86_32 || info->cpu_count != 1 ||
        info->tag_count != 5 ||
        !bytes_equal(info->bootloader_name, "bEMU-NANO", 9) ||
        !hhdm || hhdm->header.tag_size != sizeof(*hhdm) ||
        hhdm->header.tag_version != 1 || hhdm->offset != 0 ||
        !kernel || kernel->header.tag_size != sizeof(*kernel) ||
        kernel->header.tag_version != 1 ||
        kernel->physical_base != 0 || kernel->virtual_base != 0 ||
        !mmap || mmap->header.tag_size != sizeof(*mmap) + 3 * sizeof(*memory) ||
        mmap->header.tag_version != 1 ||
        mmap->entry_count != 3 || mmap->entry_size != sizeof(*memory)) {
        st = BBP_ERR_SIZE;
        goto out;
    }
    memory = (const struct bbp_memory_entry *)(mmap + 1);
    if (memory[0].base != 0 || memory[0].length != 0xA0000 ||
        memory[0].type != BBP_MEM_USABLE ||
        memory[1].base != 0xA0000 || memory[1].length != 0x60000 ||
        memory[1].type != BBP_MEM_RESERVED ||
        memory[2].base != 0x100000 || memory[2].length != 0x700000 ||
        memory[2].type != BBP_MEM_USABLE) {
        st = BBP_ERR_SIZE;
        goto out;
    }

    cmdline = (const struct bbp_tag_cmdline *)
        bbp_find_tag(&l01_boot_ctx, BBP_TAG_CMDLINE);
    hypervisor = (const struct bbp_tag_hypervisor *)
        bbp_find_tag(&l01_boot_ctx, BBP_TAG_HYPERVISOR);
    if (!cmdline || cmdline->header.tag_size != sizeof(*cmdline) ||
        cmdline->header.tag_version != 1 ||
        !hypervisor || hypervisor->header.tag_size != sizeof(*hypervisor) ||
        hypervisor->header.tag_version != 1 ||
        !hypervisor->present || !bytes_equal(hypervisor->vendor, "bEMU", 4)) {
        st = BBP_ERR_SIZE;
        goto out;
    }
    st = bbp_verify_blob(&l01_boot_ctx, cmdline->string, cmdline->length,
                         cmdline->string_crc, 0);
    command = (const char *)bbp_phys_to_virt(&l01_boot_ctx, cmdline->string);
    if (st == BBP_OK) {
        if (command &&
                   cmdline->length == sizeof(BBP_L01_1991_CMDLINE) - 1 &&
                   bytes_equal(command, BBP_L01_1991_CMDLINE,
                               cmdline->length)) {
            l01_command = BBP_L01_1991_CMDLINE;
            l01_experience = "1991";
        } else if (command &&
                   cmdline->length == sizeof(BBP_L01_ALIVE_CMDLINE) - 1 &&
                   bytes_equal(command, BBP_L01_ALIVE_CMDLINE,
                               cmdline->length)) {
            l01_command = BBP_L01_ALIVE_CMDLINE;
            l01_experience = "alive";
        } else {
            st = BBP_ERR_SIZE;
        }
    }

out:
    printk("[bbp] bEMU handoff: %s", bbp_strstatus(st));
    if (st == BBP_OK) {
        l01_boot_ctx_valid = 1;
        printk(", %u tags, %s\n", (unsigned)info->tag_count,
               l01_command);
    } else
        printk(" (non-fatal, kernel continues)\n");
    return st;
}

const struct bbp_kctx *bbp_linux01_boot_ctx(void)
{
    return l01_boot_ctx_valid ? &l01_boot_ctx : (const struct bbp_kctx *)0;
}

const char *bbp_linux01_experience(void)
{
    return l01_boot_ctx_valid ? l01_experience : (const char *)0;
}
