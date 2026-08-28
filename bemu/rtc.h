#ifndef BEMU_RTC_H
#define BEMU_RTC_H

#include <stdint.h>
#include <time.h>

struct rtc_state {
    uint8_t registers[128];
};

int rtc_init_at(struct rtc_state *rtc, const char *experience, time_t now);
uint8_t rtc_read(const struct rtc_state *rtc, uint8_t index);

#endif
