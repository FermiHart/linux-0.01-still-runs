#include "loader.h"
#include "kernel_image.h"
#include "machine.h"
#include "memory.h"

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

static ssize_t kernel_read(int fd, void *buffer, size_t size, void *opaque)
{
    (void)opaque;
    return read(fd, buffer, size);
}

static enum bemu_load_status read_full(int fd, void *buffer, size_t size,
                                       int *saved_errno,
                                       bemu_kernel_reader reader,
                                       void *reader_opaque)
{
    uint8_t *p = buffer;
    while (size) {
        ssize_t got = reader(fd, p, size, reader_opaque);
        if (got < 0) {
            if (errno == EINTR)
                continue;
            *saved_errno = errno;
            return BEMU_LOAD_READ_FAILED;
        }
        if (!got)
            return BEMU_LOAD_READ_FAILED;
        p += got;
        size -= (size_t)got;
    }
    return BEMU_LOAD_OK;
}

static uint64_t decode_le64(const uint8_t value[8])
{
    uint64_t result = 0;
    unsigned i;

    for (i = 0; i < 8; i++)
        result |= (uint64_t)value[i] << (i * 8);
    return result;
}

enum bemu_load_status bemu_validate_kernel_range(uint64_t kernel_base,
                                                  size_t kernel_size,
                                                  size_t ram_size)
{
    struct bemu_memory_range kernel = { kernel_base, kernel_size };
    struct bemu_memory_range gdt = { GDT_GPA, 24 };
    struct bemu_memory_range handoff = {
        BBP_L01_HANDOFF_PHYS,
        BBP_L01_HANDOFF_END - BBP_L01_HANDOFF_PHYS,
    };

    if (!kernel_size)
        return BEMU_LOAD_EMPTY;
    if (kernel_size > KERNEL_MAX)
        return BEMU_LOAD_TOO_LARGE;
    if (!bemu_memory_range_fits(ram_size, kernel))
        return BEMU_LOAD_OUTSIDE_RAM;
    if (bemu_memory_ranges_overlap(kernel, gdt) ||
        bemu_memory_ranges_overlap(kernel, handoff))
        return BEMU_LOAD_RESERVED_OVERLAP;
    return BEMU_LOAD_OK;
}

enum bemu_load_status bemu_validate_kernel_load(size_t kernel_size,
                                                 size_t ram_size)
{
    return bemu_validate_kernel_range(0, kernel_size, ram_size);
}

enum bemu_load_status bemu_load_kernel_with_reader(
    const char *path, uint8_t *ram, size_t ram_size, size_t *loaded_size,
    int *saved_errno, bemu_kernel_reader reader, void *reader_opaque)
{
    struct stat st;
    uint8_t trailer[KERNEL_IMAGE_TRAILER_SIZE];
    uint64_t declared_size;
    size_t file_size, payload_size;
    enum bemu_load_status status;
    int fd;

    *loaded_size = 0;
    *saved_errno = 0;
    if (!reader)
        reader = kernel_read;
    fd = open(path, O_RDONLY);
    if (fd < 0) {
        *saved_errno = errno;
        return BEMU_LOAD_OPEN_FAILED;
    }
    if (fstat(fd, &st) < 0) {
        *saved_errno = errno;
        close(fd);
        return BEMU_LOAD_STAT_FAILED;
    }
    if (st.st_size <= 0) {
        close(fd);
        return BEMU_LOAD_EMPTY;
    }
    file_size = (size_t)st.st_size;
    if (file_size > KERNEL_MAX + KERNEL_IMAGE_TRAILER_SIZE) {
        close(fd);
        return BEMU_LOAD_TOO_LARGE;
    }
    if (file_size < KERNEL_IMAGE_TRAILER_SIZE ||
        lseek(fd, (off_t)(file_size - KERNEL_IMAGE_TRAILER_SIZE), SEEK_SET) < 0) {
        close(fd);
        return BEMU_LOAD_BAD_IMAGE;
    }
    status = read_full(fd, trailer, sizeof(trailer), saved_errno,
                       kernel_read, NULL);
    if (status != BEMU_LOAD_OK) {
        close(fd);
        return status;
    }
    if (memcmp(trailer, KERNEL_IMAGE_MAGIC, KERNEL_IMAGE_MAGIC_SIZE) != 0) {
        close(fd);
        return BEMU_LOAD_BAD_IMAGE;
    }
    declared_size = decode_le64(trailer + KERNEL_IMAGE_MAGIC_SIZE);
    if (declared_size > SIZE_MAX ||
        declared_size + KERNEL_IMAGE_TRAILER_SIZE != file_size) {
        close(fd);
        return BEMU_LOAD_SIZE_MISMATCH;
    }
    payload_size = (size_t)declared_size;
    status = bemu_validate_kernel_load(payload_size, ram_size);
    if (status != BEMU_LOAD_OK) {
        close(fd);
        return status;
    }
    if (lseek(fd, 0, SEEK_SET) < 0) {
        *saved_errno = errno;
        close(fd);
        return BEMU_LOAD_READ_FAILED;
    }
    status = read_full(fd, ram, payload_size, saved_errno, reader,
                       reader_opaque);
    close(fd);
    if (status == BEMU_LOAD_OK)
        *loaded_size = payload_size;
    return status;
}

enum bemu_load_status bemu_load_kernel(const char *path, uint8_t *ram,
                                        size_t ram_size, size_t *loaded_size,
                                        int *saved_errno)
{
    return bemu_load_kernel_with_reader(path, ram, ram_size, loaded_size,
                                        saved_errno, NULL, NULL);
}

const char *bemu_load_status_string(enum bemu_load_status status)
{
    switch (status) {
    case BEMU_LOAD_OK:
        return "ok";
    case BEMU_LOAD_OPEN_FAILED:
        return "could not open kernel";
    case BEMU_LOAD_STAT_FAILED:
        return "could not stat kernel";
    case BEMU_LOAD_EMPTY:
        return "kernel is empty";
    case BEMU_LOAD_TOO_LARGE:
        return "kernel exceeds 524288-byte limit";
    case BEMU_LOAD_OUTSIDE_RAM:
        return "kernel does not fit guest RAM";
    case BEMU_LOAD_RESERVED_OVERLAP:
        return "kernel overlaps reserved guest memory";
    case BEMU_LOAD_READ_FAILED:
        return "kernel read was incomplete";
    case BEMU_LOAD_BAD_IMAGE:
        return "kernel image has no valid L01KIMG1 trailer";
    case BEMU_LOAD_SIZE_MISMATCH:
        return "kernel image size does not match its trailer";
    }
    return "unknown kernel loading error";
}

static uint64_t monotonic_ns(void)
{
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0)
        die("clock_gettime");
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

int build_bbp_handoff(struct machine *m, size_t kernel_size)
{
    struct bemu_memory_range handoff = {
        BBP_L01_HANDOFF_PHYS,
        BBP_L01_HANDOFF_END - BBP_L01_HANDOFF_PHYS,
    };
    struct bbp_info *info;
    uint8_t *arena;
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
    const char *command;
    uint64_t now;

    if (!m->ram || m->ram_size != RAM_SIZE ||
        !bemu_memory_range_fits(m->ram_size, handoff))
        return -1;
    now = monotonic_ns();
    info = (struct bbp_info *)(m->ram + BBP_L01_HANDOFF_PHYS);
    arena = (uint8_t *)(info + 1);
    memset(info, 0, BBP_L01_HANDOFF_END - BBP_L01_HANDOFF_PHYS);
    bbp_builder_init(&b, arena, BBP_L01_HANDOFF_PHYS + sizeof(*info), capacity);

    command = !strcmp(m->experience, "1991") ?
        BBP_L01_1991_CMDLINE : BBP_L01_ALIVE_CMDLINE;
    command_phys = bbp_arena_strdup(&b, command, &command_len);

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
        entries[2].length = m->ram_size - 0x100000;
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
        cmdline->string_crc = bbp_crc64(command, command_len);
    }

    hypervisor = bbp_alloc_tag(&b, BBP_TAG_HYPERVISOR, 1, sizeof(*hypervisor));
    if (hypervisor) {
        hypervisor->present = 1;
        memcpy(hypervisor->vendor, "bEMU", 4);
    }

    if (!command_phys || b.overflow)
        return -1;

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
             kernel_size, command);
    return 0;
}
