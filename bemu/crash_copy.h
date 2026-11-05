/* Author: F E R M I ∞ H A R T <contact@fermihart.com>
 * SPDX-License-Identifier: Unlicense
 * Crash experiments never map the caller's source image writable.
 */
#ifndef BEMU_CRASH_COPY_H
#define BEMU_CRASH_COPY_H
#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

static inline int copy_crash_image(const char *source, const char *destination)
{
    int input = -1, output = -1, saved;
    struct stat st;
    char buffer[65536];
    ssize_t amount, at, written;
    input = open(source, O_RDONLY);
    if (input < 0) return -1;
    if (fstat(input, &st) || !S_ISREG(st.st_mode) || st.st_size <= 0 ||
        st.st_size > 1024LL * 1024 * 1024) {
        close(input); errno = EINVAL; return -1;
    }
    /* O_EXCL also rejects an existing symlink; never clobber a destination. */
    output = open(destination, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (output < 0) { saved = errno; close(input); errno = saved; return -1; }
    for (;;) {
        amount = read(input, buffer, sizeof buffer);
        if (amount < 0 && errno == EINTR) continue;
        if (amount < 0) goto error;
        if (!amount) break;
        for (at = 0; at < amount; at += written) {
            written = write(output, buffer + at, (size_t)(amount - at));
            if (written < 0 && errno == EINTR) { written = 0; continue; }
            if (written <= 0) { if (!written) errno = EIO; goto error; }
        }
    }
    if (close(output) < 0) { output = -1; goto error; }
    close(input);
    return 0;
error:
    saved = errno;
    if (output >= 0) close(output);
    close(input);
    unlink(destination);
    errno = saved;
    return -1;
}
#endif
