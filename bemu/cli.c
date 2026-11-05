/*
 * Maintainer and adaptation: F E R M I ∞ H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#include "cli.h"
#include "experience.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

void cli_usage(const char *program)
{
    fprintf(stderr, "usage: %s [--kernel FILE] [--root FILE] "
            "[--keys TEXT] [--expect TEXT] [--trace] [--trace-file PATH] "
            "[--trace-syscalls] [--no-timer] [--raw-console] [--max-exits N] "
            "[--experience 1991|alive] "
            "[--power-cut-lba N --power-cut-phase accepted|payload|committed|irq --power-cut-copy NEW_FILE]\n", program);
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
    int root_explicit = 0;
    out->kernel = "build/kernel.bin";
    out->root = "build/root.img";
    out->script = NULL;
    out->expect = NULL;
    out->trace_file = NULL;
    out->experience = EXPERIENCE_ALIVE;
    out->max_exits = 50000000;
    out->trace = 0;
    out->no_timer = 0;
    out->raw_console = 0;
    out->trace_syscalls = 0;
    out->power_cut_lba = -1;
    out->power_cut_phase = 0;
    out->power_cut_copy = NULL;

    for (i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--kernel") && i + 1 < argc) {
            out->kernel = argv[++i];
        } else if (!strcmp(argv[i], "--root") && i + 1 < argc) {
            out->root = argv[++i];
            root_explicit = 1;
        } else if (!strcmp(argv[i], "--keys") && i + 1 < argc) {
            out->script = argv[++i];
        } else if (!strcmp(argv[i], "--expect") && i + 1 < argc) {
            out->expect = argv[++i];
        } else if (!strcmp(argv[i], "--experience") && i + 1 < argc) {
            out->experience = argv[++i];
            if (strcmp(out->experience, EXPERIENCE_1991) &&
                strcmp(out->experience, EXPERIENCE_ALIVE)) {
                fprintf(stderr, "[bemu-linux01] invalid experience: %s\n",
                        out->experience);
                return -1;
            }
        } else if (!strcmp(argv[i], "--max-exits") && i + 1 < argc) {
            if (parse_max_exits(argv[++i], &out->max_exits) < 0) {
                fprintf(stderr, "[bemu-linux01] invalid --max-exits value: %s\n", argv[i]);
                return -1;
            }
        } else if (!strcmp(argv[i], "--power-cut-lba") && i + 1 < argc) {
            const char *value = argv[++i];
            if (!strcmp(value, "0"))
                out->power_cut_lba = 0;
            else if (parse_max_exits(value, &out->power_cut_lba) < 0 ||
                     (unsigned long)out->power_cut_lba > UINT_MAX)
                return -1;
        } else if (!strcmp(argv[i], "--power-cut-copy") && i + 1 < argc) {
            out->power_cut_copy = argv[++i];
        } else if (!strcmp(argv[i], "--power-cut-phase") && i + 1 < argc) {
            const char *phase = argv[++i];
            if (!strcmp(phase, "accepted")) out->power_cut_phase = 1;
            else if (!strcmp(phase, "payload")) out->power_cut_phase = 2;
            else if (!strcmp(phase, "committed")) out->power_cut_phase = 3;
            else if (!strcmp(phase, "irq")) out->power_cut_phase = 4;
            else return -1;
        } else if (!strcmp(argv[i], "--trace")) {
            out->trace = 1;
        } else if (!strcmp(argv[i], "--trace-file") && i + 1 < argc) {
            out->trace_file = argv[++i];
        } else if (!strcmp(argv[i], "--trace-syscalls")) {
            out->trace_syscalls = 1;
        } else if (!strcmp(argv[i], "--no-timer")) {
            out->no_timer = 1;
        } else if (!strcmp(argv[i], "--raw-console")) {
            out->raw_console = 1;
        } else {
            return -1;
        }
    }
    /* The runner exclusively creates and maps a copy, never this root source. */
    if ((out->power_cut_lba >= 0) != (out->power_cut_phase != 0) ||
        (out->power_cut_phase != 0) != (out->power_cut_copy != NULL) ||
        (out->power_cut_phase && !root_explicit))
        return -1;
    if (!strcmp(out->experience, EXPERIENCE_1991) && !root_explicit)
        out->root = "build/root-1991.img";
    return 0;
}
