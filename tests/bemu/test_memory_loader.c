#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#include "../../bbp/linux01_handoff.h"
#include "../../bemu/kernel_image.h"
#include "../../bemu/loader.h"
#include "../../bemu/machine.h"
#include "../../bemu/memory.h"

static int failures;
static int mapper_calls;

void die(const char *what)
{
    perror(what);
    abort();
}

void fail(const char *what)
{
    fprintf(stderr, "FAIL: unexpected production failure: %s\n", what);
    abort();
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

static void *fail_mapper(size_t size, void *opaque)
{
    (void)size;
    (void)opaque;
    mapper_calls++;
    errno = ENOMEM;
    return MAP_FAILED;
}

static ssize_t truncated_reader(int fd, void *buffer, size_t size, void *opaque)
{
    size_t *remaining = opaque;
    ssize_t got;

    if (!*remaining)
        return 0;
    if (size > *remaining)
        size = *remaining;
    got = read(fd, buffer, size);
    if (got > 0)
        *remaining -= (size_t)got;
    return got;
}

static int finish_kernel_image(int fd, size_t payload_size)
{
    uint8_t size_le[8];
    unsigned i;

    if (ftruncate(fd, (off_t)(payload_size + KERNEL_IMAGE_TRAILER_SIZE)) < 0 ||
        lseek(fd, (off_t)payload_size, SEEK_SET) != (off_t)payload_size ||
        write(fd, KERNEL_IMAGE_MAGIC, KERNEL_IMAGE_MAGIC_SIZE) !=
              KERNEL_IMAGE_MAGIC_SIZE)
        return -1;
    for (i = 0; i < sizeof(size_le); i++)
        size_le[i] = (uint8_t)((uint64_t)payload_size >> (i * 8));
    return write(fd, size_le, sizeof(size_le)) == (ssize_t)sizeof(size_le) ? 0 : -1;
}

static void test_ranges(void)
{
    struct bemu_memory_range last = { RAM_SIZE - 1, 1 };
    struct bemu_memory_range outside = { RAM_SIZE - 1, 2 };
    struct bemu_memory_range wrapping = { UINT64_MAX - 1, 4 };
    struct bemu_memory_range kernel = { 0, KERNEL_MAX };
    struct bemu_memory_range adjacent = { KERNEL_MAX, 1 };
    struct bemu_memory_range overlap = { KERNEL_MAX - 1, 2 };

    check(bemu_memory_range_fits(RAM_SIZE, last), "last RAM byte fits");
    check(!bemu_memory_range_fits(RAM_SIZE, outside), "range past RAM is rejected");
    check(!bemu_memory_range_fits(UINT64_MAX, wrapping), "wrapping range is rejected");
    check(!bemu_memory_ranges_overlap(kernel, adjacent), "adjacent ranges do not overlap");
    check(bemu_memory_ranges_overlap(kernel, overlap), "partial overlap is detected");
    check(bemu_memory_range_fits(RAM_SIZE,
          (struct bemu_memory_range){ BBP_L01_HANDOFF_PHYS,
                                      BBP_L01_HANDOFF_END - BBP_L01_HANDOFF_PHYS }),
          "BBP window fits historical RAM");
    check(!bemu_memory_range_fits(BBP_L01_HANDOFF_END - 1,
           (struct bemu_memory_range){ BBP_L01_HANDOFF_PHYS,
                                       BBP_L01_HANDOFF_END - BBP_L01_HANDOFF_PHYS }),
          "BBP window rejects short RAM");
}

static void test_ram_mapping(void)
{
    struct machine m;

    memset(&m, 0, sizeof m);
    mapper_calls = 0;
    check(bemu_memory_map_ram(&m, RAM_SIZE - 1, fail_mapper, NULL) ==
          BEMU_MEMORY_INVALID_SIZE, "RAM below 8 MiB is rejected");
    check(mapper_calls == 0, "invalid RAM size does not call mapper");
    check(bemu_memory_map_ram(&m, RAM_SIZE, fail_mapper, NULL) ==
          BEMU_MEMORY_ALLOCATION_FAILED, "ENOMEM injection is deterministic");
    check(mapper_calls == 1 && m.ram == NULL && m.ram_size == 0,
          "failed mapping leaves no partial state");
    check(bemu_memory_map_ram(&m, RAM_SIZE, NULL, NULL) == BEMU_MEMORY_OK,
          "exactly 8 MiB maps successfully");
    check(m.ram != NULL && m.ram_size == RAM_SIZE, "successful RAM size is recorded");
    bemu_memory_unmap_ram(&m);
    check(m.ram == NULL && m.ram_size == 0, "RAM unmap clears state");
}

static void test_bbp_memory_limit(void)
{
    struct machine m;

    memset(&m, 0, sizeof m);
    m.ram_size = BBP_L01_HANDOFF_END;
    m.ram = calloc(1, m.ram_size);
    m.experience = "alive";
    check(m.ram != NULL, "short-RAM BBP fixture allocated");
    if (!m.ram)
        return;
    check(build_bbp_handoff(&m, 1) < 0,
          "BBP handoff rejects incomplete guest layout");
    free(m.ram);
}

static void test_kernel_limits(void)
{
    char path[] = "/tmp/bemu-loader-XXXXXX";
    uint8_t *ram;
    size_t loaded = 0;
    int saved_errno = 0;
    int fd = mkstemp(path);
    uint8_t tail = 0x5a;

    check(fd >= 0, "kernel fixture created");
    if (fd < 0)
        return;
    check(ftruncate(fd, KERNEL_MAX) == 0, "exact-limit kernel payload sized");
    check(lseek(fd, KERNEL_MAX - 1, SEEK_SET) == KERNEL_MAX - 1,
          "kernel fixture seeks to final byte");
    check(write(fd, &tail, 1) == 1, "kernel fixture final byte written");
    check(finish_kernel_image(fd, KERNEL_MAX) == 0,
          "exact-limit kernel trailer written");
    close(fd);

    ram = malloc(RAM_SIZE);
    check(ram != NULL, "test RAM allocated");
    if (!ram) {
        unlink(path);
        return;
    }
    memset(ram, 0, RAM_SIZE);
    check(bemu_load_kernel(path, ram, RAM_SIZE, &loaded, &saved_errno) ==
          BEMU_LOAD_OK, "512 KiB kernel boundary is accepted");
    check(loaded == KERNEL_MAX && ram[KERNEL_MAX - 1] == tail &&
          ram[KERNEL_MAX] == 0, "only kernel payload bytes are loaded");

    fd = open(path, O_WRONLY);
    check(fd >= 0 && finish_kernel_image(fd, KERNEL_MAX + 1) == 0,
          "over-limit kernel fixture sized");
    if (fd >= 0)
        close(fd);
    memset(ram, 0xa5, RAM_SIZE);
    loaded = 123;
    check(bemu_load_kernel(path, ram, RAM_SIZE, &loaded, &saved_errno) ==
          BEMU_LOAD_TOO_LARGE, "kernel above 512 KiB is rejected");
    check(loaded == 0 && ram[0] == 0xa5, "rejected kernel does not modify RAM");
    check(bemu_validate_kernel_load(KERNEL_MAX, KERNEL_MAX - 1) ==
          BEMU_LOAD_OUTSIDE_RAM, "kernel outside supplied RAM is rejected");
    check(bemu_validate_kernel_load(0, RAM_SIZE) == BEMU_LOAD_EMPTY,
          "empty kernel is rejected");
    check(bemu_validate_kernel_range(GDT_GPA - 1, 2, RAM_SIZE) ==
          BEMU_LOAD_RESERVED_OVERLAP, "kernel overlap with GDT is rejected");
    check(bemu_validate_kernel_range(BBP_L01_HANDOFF_PHYS, 1, RAM_SIZE) ==
          BEMU_LOAD_RESERVED_OVERLAP, "kernel overlap with BBP is rejected");
    check(bemu_validate_kernel_range(GDT_GPA - 1, 1, RAM_SIZE) ==
          BEMU_LOAD_OK, "kernel adjacent to GDT is accepted");
    check(strcmp(bemu_load_status_string(BEMU_LOAD_RESERVED_OVERLAP),
                 "kernel overlaps reserved guest memory") == 0,
          "reserved overlap has a stable diagnostic");

    fd = open(path, O_WRONLY | O_TRUNC);
    check(fd >= 0 && finish_kernel_image(fd, 8192) == 0,
          "truncated-read kernel fixture sized");
    if (fd >= 0)
        close(fd);
    {
        size_t readable = 4096;

        loaded = 123;
        saved_errno = 0;
        check(bemu_load_kernel_with_reader(path, ram, RAM_SIZE, &loaded,
              &saved_errno, truncated_reader, &readable) ==
              BEMU_LOAD_READ_FAILED, "truncated kernel payload is rejected");
        check(loaded == 0 && saved_errno == 0,
              "truncated payload returns structured state");
        check(strcmp(bemu_load_status_string(BEMU_LOAD_READ_FAILED),
                     "kernel read was incomplete") == 0,
              "truncated payload has a stable diagnostic");
    }

    fd = open(path, O_WRONLY | O_TRUNC);
    check(fd >= 0 && ftruncate(fd, 8192) == 0,
          "legacy raw kernel fixture sized");
    if (fd >= 0)
        close(fd);
    loaded = 123;
    memset(ram, 0xa5, RAM_SIZE);
    check(bemu_load_kernel(path, ram, RAM_SIZE, &loaded, &saved_errno) ==
          BEMU_LOAD_BAD_IMAGE, "raw kernel without trailer is rejected");
    check(loaded == 0 && ram[0] == 0xa5 && ram[8191] == 0xa5,
          "invalid kernel trailer leaves RAM and loaded size unchanged");

    fd = open(path, O_WRONLY | O_TRUNC);
    check(fd >= 0 && finish_kernel_image(fd, 8192) == 0 &&
          ftruncate(fd, 8192 + KERNEL_IMAGE_TRAILER_SIZE - 1) == 0,
          "short kernel trailer fixture created");
    if (fd >= 0)
        close(fd);
    memset(ram, 0xa5, RAM_SIZE);
    check(bemu_load_kernel(path, ram, RAM_SIZE, &loaded, &saved_errno) ==
          BEMU_LOAD_BAD_IMAGE, "one-byte-short kernel trailer is rejected");
    check(ram[0] == 0xa5 && ram[8191] == 0xa5,
          "short trailer rejection leaves RAM unchanged");

    fd = open(path, O_RDWR | O_TRUNC);
    check(fd >= 0 && finish_kernel_image(fd, 8192) == 0 &&
          ftruncate(fd, 4096 + KERNEL_IMAGE_TRAILER_SIZE) == 0 &&
          lseek(fd, 4096, SEEK_SET) == 4096 &&
          write(fd, KERNEL_IMAGE_MAGIC, KERNEL_IMAGE_MAGIC_SIZE) ==
              KERNEL_IMAGE_MAGIC_SIZE,
          "kernel size-mismatch fixture created");
    if (fd >= 0) {
        uint8_t size_le[8];
        unsigned i;
        for (i = 0; i < sizeof(size_le); i++)
            size_le[i] = (uint8_t)((uint64_t)8192 >> (i * 8));
        check(write(fd, size_le, sizeof(size_le)) == (ssize_t)sizeof(size_le),
              "kernel mismatch length written");
        close(fd);
    }
    memset(ram, 0xa5, RAM_SIZE);
    check(bemu_load_kernel(path, ram, RAM_SIZE, &loaded, &saved_errno) ==
          BEMU_LOAD_SIZE_MISMATCH,
          "kernel trailer length mismatch is rejected");
    check(ram[0] == 0xa5 && ram[8191] == 0xa5,
          "length mismatch rejection leaves RAM unchanged");

    free(ram);
    unlink(path);
}

int main(void)
{
    test_ranges();
    test_ram_mapping();
    test_bbp_memory_limit();
    test_kernel_limits();
    if (failures) {
        fprintf(stderr, "\n%d test(s) failed\n", failures);
        return 1;
    }
    printf("\nall memory/loader tests passed\n");
    return 0;
}
