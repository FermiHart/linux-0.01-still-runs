#ifndef BEMU_LOADER_H
#define BEMU_LOADER_H

#include <stddef.h>
#include <stdint.h>

struct machine;

size_t load_kernel(const char *path, uint8_t *ram);
void build_bbp_handoff(struct machine *m, size_t kernel_size);

#endif
