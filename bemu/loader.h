#ifndef BEMU_LOADER_H
#define BEMU_LOADER_H

#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>

struct machine;

enum bemu_load_status {
    BEMU_LOAD_OK,
    BEMU_LOAD_OPEN_FAILED,
    BEMU_LOAD_STAT_FAILED,
    BEMU_LOAD_EMPTY,
    BEMU_LOAD_TOO_LARGE,
    BEMU_LOAD_OUTSIDE_RAM,
    BEMU_LOAD_RESERVED_OVERLAP,
    BEMU_LOAD_READ_FAILED,
};

typedef ssize_t (*bemu_kernel_reader)(int fd, void *buffer, size_t size,
                                      void *opaque);

enum bemu_load_status bemu_validate_kernel_range(uint64_t kernel_base,
                                                  size_t kernel_size,
                                                  size_t ram_size);
enum bemu_load_status bemu_validate_kernel_load(size_t kernel_size,
                                                 size_t ram_size);
enum bemu_load_status bemu_load_kernel(const char *path, uint8_t *ram,
                                        size_t ram_size, size_t *loaded_size,
                                        int *saved_errno);
enum bemu_load_status bemu_load_kernel_with_reader(
    const char *path, uint8_t *ram, size_t ram_size, size_t *loaded_size,
    int *saved_errno, bemu_kernel_reader reader, void *reader_opaque);
const char *bemu_load_status_string(enum bemu_load_status status);
int build_bbp_handoff(struct machine *m, size_t kernel_size);

#endif
