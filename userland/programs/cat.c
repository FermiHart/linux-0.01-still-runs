/* cat.c - Minimal Unix cat(1) for Linux 0.01. */

#include "libc.h"

#define O_RDONLY 0

static int copy_fd(int fd)
{
    char buf[512];
    ssize_t n;

    while ((n = read(fd, buf, sizeof(buf))) > 0)
        if (write(1, buf, (size_t)n) != n)
            return 1;
    return n < 0;
}

int main(int argc, char **argv)
{
    int i, fd, status = 0;

    if (argc < 2)
        return copy_fd(0);
    for (i = 1; i < argc; i++) {
        fd = open(argv[i], O_RDONLY);
        if (fd < 0) {
            status = 1;
            continue;
        }
        if (copy_fd(fd))
            status = 1;
        close(fd);
    }
    return status;
}
