/*
 * Author: F E R M I INFINITY H A R T <contact@fermihart.com>
 * SPDX-License-Identifier: Unlicense
 */

/* yes.c — Classic Unix yes(1) for Linux 0.01
 *
 * Prints its argument (or "y") forever, one line per iteration.
 * Stops only when killed.  Uses real syscalls only.
 */

#include "libc.h"

int main(int argc, char **argv)
{
    const char *msg = (argc > 1) ? argv[1] : "y";
    size_t len = strlen(msg);

    for (;;) {
        if (write(1, msg, len) != (ssize_t)len || write(1, "\n", 1) != 1)
            return 1;
    }
}
