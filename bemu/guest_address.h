/* Author: F E R M I ∞ H A R T <contact@fermihart.com>
 * SPDX-License-Identifier: BSD-3-Clause
 * Bounded protected-mode instruction fetch for the Linux 0.01 observer.
 * Translation is supplied by KVM in production and a mapping fixture in tests.
 */
#ifndef BEMU_GUEST_ADDRESS_H
#define BEMU_GUEST_ADDRESS_H
#include <stddef.h>
#include <stdint.h>

typedef int (*guest_translate_fn)(void *, uint32_t, uint64_t *);

static inline int guest_fetch32(const uint8_t *ram, size_t ram_size,
                               uint64_t cs_base, uint32_t cs_limit,
                               uint64_t eip, uint8_t *bytes, size_t count,
                               guest_translate_fn translate, void *context)
{
    size_t i;
    if (!ram || !bytes || !translate || !count || count > 15 ||
        eip > UINT32_MAX || cs_base > UINT32_MAX || eip > cs_limit ||
        count - 1 > (uint64_t)cs_limit - eip ||
        cs_base + eip + count - 1 > UINT32_MAX)
        return -1;
    for (i = 0; i < count; i++) {
        uint64_t physical;
        if (translate(context, (uint32_t)(cs_base + eip + i), &physical) ||
            physical >= ram_size)
            return -1;
        bytes[i] = ram[physical];
    }
    return 0;
}
#endif
