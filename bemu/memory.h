/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#ifndef BEMU_MEMORY_H
#define BEMU_MEMORY_H

#include <stddef.h>
#include <stdint.h>

struct machine;

struct bemu_memory_range {
    uint64_t base;
    uint64_t size;
};

enum bemu_memory_status {
    BEMU_MEMORY_OK,
    BEMU_MEMORY_INVALID_SIZE,
    BEMU_MEMORY_ALLOCATION_FAILED,
};

typedef void *(*bemu_memory_mapper)(size_t size, void *opaque);

int bemu_memory_range_fits(uint64_t ram_size, struct bemu_memory_range range);
int bemu_memory_ranges_overlap(struct bemu_memory_range a,
                               struct bemu_memory_range b);
enum bemu_memory_status bemu_memory_map_ram(struct machine *m, size_t size,
                                             bemu_memory_mapper mapper,
                                             void *opaque);
void bemu_memory_unmap_ram(struct machine *m);
const char *bemu_memory_status_string(enum bemu_memory_status status);

#endif
