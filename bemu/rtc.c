/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#define _POSIX_C_SOURCE 200809L
#include "rtc.h"

#include <string.h>

static uint8_t bcd(unsigned value)
{
    return (uint8_t)(((value / 10) << 4) | (value % 10));
}

int rtc_init_at(struct rtc_state *rtc, const char *experience, time_t now)
{
    struct tm snapshot;

    if (!experience || (strcmp(experience, "1991") != 0 &&
                        strcmp(experience, "alive") != 0))
        return -1;
    memset(rtc, 0, sizeof *rtc);
    if (strcmp(experience, "1991") == 0) {
        memset(&snapshot, 0, sizeof snapshot);
        snapshot.tm_year = 91;
        snapshot.tm_mon = 8;
        snapshot.tm_mday = 17;
    } else if (!gmtime_r(&now, &snapshot)) {
        return -1;
    }

    rtc->registers[0] = bcd((unsigned)snapshot.tm_sec);
    rtc->registers[2] = bcd((unsigned)snapshot.tm_min);
    rtc->registers[4] = bcd((unsigned)snapshot.tm_hour);
    rtc->registers[7] = bcd((unsigned)snapshot.tm_mday);
    rtc->registers[8] = bcd((unsigned)snapshot.tm_mon + 1);
    rtc->registers[9] = bcd((unsigned)(snapshot.tm_year % 100));
    rtc->registers[11] = 2;
    return 0;
}

uint8_t rtc_read(const struct rtc_state *rtc, uint8_t index)
{
    return rtc->registers[index & 0x7f];
}
