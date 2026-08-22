#include "loader.h"
#include "machine.h"

#include <bbp/bbp.h>
#include <bbp/bbp_crc64.h>
#include "../bbp/bbp_build.h"
#include "../bbp/linux01_handoff.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static void read_full(int fd, void *buffer, size_t size, const char *name)
{
    uint8_t *p = buffer;
    while (size) {
        ssize_t got = read(fd, p, size);
        if (got < 0) {
            if (errno == EINTR)
                continue;
            die(name);
        }
        if (!got)
            fail("short input file");
        p += got;
        size -= (size_t)got;
    }
}

size_t load_kernel(const char *path, uint8_t *ram)
{
    struct stat st;
    int fd = open(path, O_RDONLY);
    if (fd < 0)
        die(path);
    if (fstat(fd, &st) < 0)
        die("fstat kernel");
    if (st.st_size <= 0 || st.st_size > KERNEL_MAX)
        fail("kernel.bin has an invalid size");
    read_full(fd, ram, (size_t)st.st_size, path);
    close(fd);
    return (size_t)st.st_size;
}

static uint64_t monotonic_ns(void)
{
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0)
        die("clock_gettime");
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

void build_bbp_handoff(struct machine *m, size_t kernel_size)
{
    struct bbp_info *info = (struct bbp_info *)(m->ram + BBP_L01_HANDOFF_PHYS);
    uint8_t *arena = (uint8_t *)(info + 1);
    size_t capacity = BBP_L01_HANDOFF_END - BBP_L01_HANDOFF_PHYS - sizeof(*info);
    struct bbp_builder b;
    struct bbp_tag_hhdm *hhdm;
    struct bbp_tag_memory_map *mmap;
    struct bbp_memory_entry *entries;
    struct bbp_tag_kernel_address *kernel;
    struct bbp_tag_cmdline *cmdline;
    struct bbp_tag_hypervisor *hypervisor;
    bbp_phys_t command_phys;
    uint32_t command_len;
    uint64_t now = monotonic_ns();

    memset(info, 0, BBP_L01_HANDOFF_END - BBP_L01_HANDOFF_PHYS);
    bbp_builder_init(&b, arena, BBP_L01_HANDOFF_PHYS + sizeof(*info), capacity);

    command_phys = bbp_arena_strdup(&b, BBP_L01_ROOT_CMDLINE, &command_len);

    hhdm = bbp_alloc_tag(&b, BBP_TAG_HHDM, 1, sizeof(*hhdm));
    if (hhdm)
        hhdm->offset = 0;

    mmap = bbp_alloc_tag(&b, BBP_TAG_MEMORY_MAP, 1,
                         sizeof(*mmap) + 3 * sizeof(*entries));
    if (mmap) {
        mmap->entry_count = 3;
        mmap->entry_size = sizeof(*entries);
        entries = (struct bbp_memory_entry *)(mmap + 1);
        entries[0].base = 0;
        entries[0].length = 0xA0000;
        entries[0].type = BBP_MEM_USABLE;
        entries[0].attributes = BBP_MEM_ATTR_READABLE | BBP_MEM_ATTR_WRITABLE |
                                BBP_MEM_ATTR_CACHED;
        entries[1].base = 0xA0000;
        entries[1].length = 0x60000;
        entries[1].type = BBP_MEM_RESERVED;
        entries[1].attributes = BBP_MEM_ATTR_READABLE;
        entries[2].base = 0x100000;
        entries[2].length = RAM_SIZE - 0x100000;
        entries[2].type = BBP_MEM_USABLE;
        entries[2].attributes = BBP_MEM_ATTR_READABLE | BBP_MEM_ATTR_WRITABLE |
                                BBP_MEM_ATTR_CACHED;
    }

    kernel = bbp_alloc_tag(&b, BBP_TAG_KERNEL_ADDRESS, 1, sizeof(*kernel));
    if (kernel) {
        kernel->physical_base = 0;
        kernel->virtual_base = 0;
    }

    cmdline = bbp_alloc_tag(&b, BBP_TAG_CMDLINE, 1, sizeof(*cmdline));
    if (cmdline) {
        cmdline->string = command_phys;
        cmdline->length = command_len;
        cmdline->string_crc = bbp_crc64(BBP_L01_ROOT_CMDLINE, command_len);
    }

    hypervisor = bbp_alloc_tag(&b, BBP_TAG_HYPERVISOR, 1, sizeof(*hypervisor));
    if (hypervisor) {
        hypervisor->present = 1;
        memcpy(hypervisor->vendor, "bEMU", 4);
    }

    if (!command_phys || b.overflow)
        fail("BBP handoff exceeds its reserved window");

    memcpy(info->bootloader_name, "bEMU-NANO", 9);
    memcpy(info->bootloader_version, "linux01-1", 9);
    info->bootloader_uuid[0] = 0x4f4e414e2d554d45ULL;
    info->bootloader_uuid[1] = 0x31302d58554e494cULL;
    info->bootloader_start_ts = now;
    info->kernel_load_ts = now;
    info->handoff_ts = monotonic_ns();
    info->architecture = BBP_ARCH_X86_32;
    info->cpu_count = 1;
    bbp_builder_finalize(&b, info, BBP_L01_HANDOFF_PHYS);

    fprintf(stderr,
            "[bemu-linux01] BBP @ %#lx: %u tags, kernel=%zu bytes, %s\n",
            (unsigned long)BBP_L01_HANDOFF_PHYS, info->tag_count,
            kernel_size, BBP_L01_ROOT_CMDLINE);
}
