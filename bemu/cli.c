#include "cli.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

void cli_usage(const char *program)
{
    fprintf(stderr, "usage: %s [--kernel FILE] [--root FILE] "
            "[--keys TEXT] [--expect TEXT] [--trace] [--no-timer] "
            "[--raw-console] [--max-exits N]\n", program);
}

static int parse_max_exits(const char *text, long *value)
{
    unsigned long parsed = 0;
    unsigned long digit;

    if (!text || !*text)
        return -1;
    while (*text) {
        if (*text < '0' || *text > '9')
            return -1;
        digit = (unsigned long)(*text++ - '0');
        if (parsed > ((unsigned long)LONG_MAX - digit) / 10)
            return -1;
        parsed = parsed * 10 + digit;
    }
    if (!parsed)
        return -1;
    *value = (long)parsed;
    return 0;
}

int cli_parse_args(int argc, char **argv, struct cli_options *out)
{
    int i;
    out->kernel = "build/kernel.bin";
    out->root = "build/root.img";
    out->script = NULL;
    out->expect = NULL;
    out->max_exits = 50000000;
    out->trace = 0;
    out->no_timer = 0;
    out->raw_console = 0;

    for (i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--kernel") && i + 1 < argc) {
            out->kernel = argv[++i];
        } else if (!strcmp(argv[i], "--root") && i + 1 < argc) {
            out->root = argv[++i];
        } else if (!strcmp(argv[i], "--keys") && i + 1 < argc) {
            out->script = argv[++i];
        } else if (!strcmp(argv[i], "--expect") && i + 1 < argc) {
            out->expect = argv[++i];
        } else if (!strcmp(argv[i], "--max-exits") && i + 1 < argc) {
            if (parse_max_exits(argv[++i], &out->max_exits) < 0) {
                fprintf(stderr, "[bemu-linux01] invalid --max-exits value: %s\n", argv[i]);
                return -1;
            }
        } else if (!strcmp(argv[i], "--trace")) {
            out->trace = 1;
        } else if (!strcmp(argv[i], "--no-timer")) {
            out->no_timer = 1;
        } else if (!strcmp(argv[i], "--raw-console")) {
            out->raw_console = 1;
        } else {
            return -1;
        }
    }
    return 0;
}
