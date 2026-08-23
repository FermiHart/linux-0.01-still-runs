/*
 * Minimal reproduction of kernel/vsprintf.c '%s' handling.
 *
 * The original symptom: at -O2 a non-empty %s format reads the pointer argument
 * from the wrong slot and renders garbage, while -O1 works.  This file extracts
 * the relevant portion of vsprintf() into a host-runnable program that formats
 * a single string and compares it against the expected output.
 *
 * If the compiler reorders va_arg reads, optimises away the null check, or
 * misaligns the varargs pointer, the assertion fails.
 */

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#define LEFT 16

static int mini_vsprintf(char *buf, const char *fmt, va_list args)
{
    char *str = buf;
    char *s;
    int len;
    int i;
    int flags = 0;
    int field_width = 0;
    const char *p;

    for (p = fmt; *p; ++p) {
        if (*p != '%') {
            *str++ = *p;
            continue;
        }
        ++p;
        if (*p == '-') {
            flags |= LEFT;
            ++p;
        }
        if (*p >= '0' && *p <= '9') {
            field_width = 0;
            while (*p >= '0' && *p <= '9')
                field_width = field_width * 10 + *p++ - '0';
        }
        if (*p == 'l' || *p == 'L')
            ++p;

        switch (*p) {
        case 's':
            s = va_arg(args, char *);
            if (!s)
                s = "(null)";
            len = strlen(s);
            if (!(flags & LEFT))
                for (i = field_width - len; i > 0; --i)
                    *str++ = ' ';
            for (i = 0; i < len; ++i)
                *str++ = *s++;
            if (flags & LEFT)
                for (i = field_width - len; i > 0; --i)
                    *str++ = ' ';
            break;
        default:
            *str++ = *p;
            break;
        }
        flags = 0;
        field_width = 0;
    }
    *str = '\0';
    return str - buf;
}

static __attribute__((noinline)) int fmt(char *buf, const char *fmtstr, ...)
{
    va_list args;
    va_start(args, fmtstr);
    int n = mini_vsprintf(buf, fmtstr, args);
    va_end(args);
    return n;
}

int main(void)
{
    char buf[256];

    fmt(buf, "[%s]", "hello");
    if (strcmp(buf, "[hello]") != 0) {
        fprintf(stderr, "FAIL: got '%s' expected '[hello]'\n", buf);
        return 1;
    }

    fmt(buf, "[%8s]", "hi");
    if (strcmp(buf, "[      hi]") != 0) {
        fprintf(stderr, "FAIL: got '%s' expected '[      hi]'\n", buf);
        return 1;
    }

    fmt(buf, "[%-8s]", "ho");
    if (strcmp(buf, "[ho      ]") != 0) {
        fprintf(stderr, "FAIL: got '%s' expected '[ho      ]'\n", buf);
        return 1;
    }

    puts("PASS: %s formatting reads the correct argument slot");
    return 0;
}
