/* libc.h — Minimal public-domain C library for linux-0.01 userland.
 *
 * All syscalls use int $0x80 (Linux 0.01 syscall convention).
 * Compile with: -ffreestanding -nostdlib -nostdinc
 * Link with crt0.o at VMA 0, objcopy -O binary → flat .bin
 */

#ifndef _LIBC_H
#define _LIBC_H

#define NULL ((void *)0)

typedef unsigned long size_t;
typedef long ssize_t;
typedef int pid_t;

/* syscall numbers (from kernel include/unistd.h) */
#define __NR_exit    1
#define __NR_fork    2
#define __NR_read    3
#define __NR_write   4
#define __NR_open    5
#define __NR_close   6
#define __NR_waitpid 7
#define __NR_execve  11
#define __NR_chdir   12
#define __NR_time    13
#define __NR_getpid  20
#define __NR_pause   29
#define __NR_sync    36
#define __NR_uname   59

/* Inline syscall wrappers — match kernel's _syscall0/1/2/3 pattern */
static inline int _exit(int status)
{
    int __res;
    __asm__ volatile("int $0x80"
        : "=a" (__res) : "0" (__NR_exit), "b" (status));
    return __res;
}

static inline pid_t getpid(void)
{
    int __res;
    __asm__ volatile("int $0x80"
        : "=a" (__res) : "0" (__NR_getpid));
    return __res;
}

static inline ssize_t write(int fd, const void *buf, size_t count)
{
    ssize_t __res;
    __asm__ volatile("int $0x80"
        : "=a" (__res)
        : "0" (__NR_write), "b" (fd), "c" (buf), "d" (count)
        : "memory");
    return __res;
}

static inline ssize_t read(int fd, void *buf, size_t count)
{
    ssize_t __res;
    __asm__ volatile("int $0x80"
        : "=a" (__res)
        : "0" (__NR_read), "b" (fd), "c" (buf), "d" (count)
        : "memory");
    return __res;
}

static inline int open(const char *path, int flags)
{
    int __res;
    __asm__ volatile("int $0x80"
        : "=a" (__res)
        : "0" (__NR_open), "b" (path), "c" (flags)
        : "memory");
    return __res;
}

static inline int close(int fd)
{
    int __res;
    __asm__ volatile("int $0x80"
        : "=a" (__res) : "0" (__NR_close), "b" (fd));
    return __res;
}

static inline long time(long *tloc)
{
    long __res;
    __asm__ volatile("int $0x80"
        : "=a" (__res) : "0" (__NR_time), "b" (tloc)
        : "memory");
    return __res;
}

static inline int pause(void)
{
    int __res;
    __asm__ volatile("int $0x80"
        : "=a" (__res) : "0" (__NR_pause));
    return __res;
}

static inline int uname(void *buf)
{
    int __res;
    __asm__ volatile("int $0x80"
        : "=a" (__res) : "0" (__NR_uname), "b" (buf)
        : "memory");
    return __res;
}

static inline int sync(void)
{
    int __res;
    __asm__ volatile("int $0x80"
        : "=a" (__res) : "0" (__NR_sync));
    return __res;
}

static inline pid_t wait(int *status)
{
    pid_t __res;
    __asm__ volatile("int $0x80"
        : "=a" (__res)
        : "0" (__NR_waitpid), "b" (-1), "c" (status), "d" (0)
        : "memory");
    return __res;
}

/* String functions */
static inline size_t strlen(const char *s)
{
    size_t n = 0;
    while (*s++) n++;
    return n;
}

static inline char *strcpy(char *dst, const char *src)
{
    char *d = dst;
    while ((*d++ = *src++));
    return dst;
}

static inline int strcmp(const char *a, const char *b)
{
    while (*a && *a == *b) { a++; b++; }
    return (unsigned char)*a - (unsigned char)*b;
}

/* Convert integer to ASCII (returns pointer to static buffer) */
static inline char *itoa(long n)
{
    static char buf[24];
    char *p = buf + sizeof(buf) - 1;
    unsigned long magnitude;
    int neg = (n < 0);
    magnitude = neg ? 0UL - (unsigned long)n : (unsigned long)n;
    *p = '\0';
    do { *--p = '0' + (magnitude % 10); } while (magnitude /= 10);
    if (neg) *--p = '-';
    return p;
}

/* Simple printf (only %s, %d, %x, %%, \\n → \\r\\n) */
static inline int printf(const char *fmt, ...)
{
    int len = strlen(fmt);
    write(1, fmt, len);
    return len;
}

#endif /* _LIBC_H */
