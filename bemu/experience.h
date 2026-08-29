/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#ifndef BEMU_EXPERIENCE_H
#define BEMU_EXPERIENCE_H

#define EXPERIENCE_1991 "1991"
#define EXPERIENCE_ALIVE "alive"

/* bEMU boots without MBR code, leaving this pre-partition-table area available
 * for a modern host-side profile marker. */
#define EXPERIENCE_IMAGE_MARKER_OFFSET 0x180
#define EXPERIENCE_IMAGE_MARKER_1991   "L01X1991"
#define EXPERIENCE_IMAGE_MARKER_ALIVE  "L01ALIVE"
#define EXPERIENCE_IMAGE_MARKER_LEN    8

#endif
