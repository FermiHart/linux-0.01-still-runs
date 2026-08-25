#ifndef BBP_LINUX01_HANDOFF_H
#define BBP_LINUX01_HANDOFF_H

/* The handoff occupies one page-aligned 64 KiB window in the PC legacy hole.
 * Linux 0.01 identity-maps it, and its buffer cache skips this region. */
#define BBP_L01_HANDOFF_PHYS 0x000C0000UL
#define BBP_L01_HANDOFF_END  0x000D0000UL
#define BBP_L01_1991_CMDLINE "root=/dev/hd1 ide=977,5,17 experience=1991"
#define BBP_L01_ALIVE_CMDLINE "root=/dev/hd1 ide=977,5,17 experience=alive"

#endif
