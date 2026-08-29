/*
 * Author: F E R M I INFINITY H A R T <contact@fermihart.com>
 * SPDX-License-Identifier: Unlicense
 */

#ifndef _LINUX_BEMU_H
#define _LINUX_BEMU_H

/* Explicit guest-to-bEMU power requests; completion still requires cli; hlt. */
#define BEMU_POWER_PORT    0x8900
#define BEMU_POWER_HALT    0
#define BEMU_POWER_REBOOT  1

#endif
