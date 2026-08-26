#include "memory.h"
#include "machine.h"

#include <sys/mman.h>

static void *map_guest_ram(size_t size, void *opaque)
{
    (void)opaque;
    return mmap(NULL, size, PROT_READ | PROT_WRITE,
                MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
}

int bemu_memory_range_fits(uint64_t ram_size, struct bemu_memory_range range)
{
    return range.base <= ram_size && range.size <= ram_size - range.base;
}

int bemu_memory_ranges_overlap(struct bemu_memory_range a,
                               struct bemu_memory_range b)
{
    uint64_t a_end, b_end;

    if (!a.size || !b.size)
        return 0;
    if (a.size > UINT64_MAX - a.base || b.size > UINT64_MAX - b.base)
        return 1;
    a_end = a.base + a.size;
    b_end = b.base + b.size;
    return a.base < b_end && b.base < a_end;
}

enum bemu_memory_status bemu_memory_map_ram(struct machine *m, size_t size,
                                             bemu_memory_mapper mapper,
                                             void *opaque)
{
    void *mapping;

    if (size != RAM_SIZE || m->ram || m->ram_size)
        return BEMU_MEMORY_INVALID_SIZE;
    if (!mapper)
        mapper = map_guest_ram;
    mapping = mapper(size, opaque);
    if (mapping == MAP_FAILED)
        return BEMU_MEMORY_ALLOCATION_FAILED;
    m->ram = mapping;
    m->ram_size = size;
    return BEMU_MEMORY_OK;
}

void bemu_memory_unmap_ram(struct machine *m)
{
    if (m->ram && m->ram != MAP_FAILED && m->ram_size)
        munmap(m->ram, m->ram_size);
    m->ram = NULL;
    m->ram_size = 0;
}

const char *bemu_memory_status_string(enum bemu_memory_status status)
{
    switch (status) {
    case BEMU_MEMORY_OK:
        return "ok";
    case BEMU_MEMORY_INVALID_SIZE:
        return "guest RAM must be exactly 8 MiB";
    case BEMU_MEMORY_ALLOCATION_FAILED:
        return "could not allocate 8 MiB guest RAM";
    }
    return "unknown memory error";
}
