/*
 * Author: F E R M I INFINITY H A R T <contact@fermihart.com>
 * SPDX-License-Identifier: Unlicense
 */

#include "../../bemu/rtc.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static void require_byte(const char *name, uint8_t actual, uint8_t expected)
{
    if (actual == expected)
        return;
    fprintf(stderr, "%s: got 0x%02x, expected 0x%02x\n",
            name, actual, expected);
    exit(1);
}

static void require_snapshot(const struct rtc_state *rtc,
                             uint8_t year, uint8_t month, uint8_t day,
                             uint8_t hour, uint8_t minute, uint8_t second)
{
    require_byte("year", rtc_read(rtc, 9), year);
    require_byte("month", rtc_read(rtc, 8), month);
    require_byte("day", rtc_read(rtc, 7), day);
    require_byte("hour", rtc_read(rtc, 4), hour);
    require_byte("minute", rtc_read(rtc, 2), minute);
    require_byte("second", rtc_read(rtc, 0), second);
    require_byte("status A", rtc_read(rtc, 10), 0x00);
    require_byte("status B", rtc_read(rtc, 11), 0x02);
    require_byte("unknown register", rtc_read(rtc, 0x7f), 0x00);
}

int main(void)
{
    struct rtc_state historical;
    struct rtc_state alive;

    rtc_init_at(&historical, "1991", 1700000000);
    require_snapshot(&historical, 0x91, 0x09, 0x17, 0x00, 0x00, 0x00);

    rtc_init_at(&alive, "alive", 1700000000);
    require_snapshot(&alive, 0x23, 0x11, 0x14, 0x22, 0x13, 0x20);

    if (rtc_init_at(&alive, NULL, 1700000000) == 0 ||
        rtc_init_at(&alive, "invalid", 1700000000) == 0) {
        fputs("invalid RTC profile was accepted\n", stderr);
        return 1;
    }

    puts("ok  RTC profile snapshots are deterministic, coherent, and validated");
    return 0;
}
