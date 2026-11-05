/*
 * Maintainer and adaptation: F E R M I ∞ H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#ifndef BEMU_CLI_H
#define BEMU_CLI_H

struct cli_options {
    const char *kernel;
    const char *root;
    const char *script;
    const char *expect;
    const char *trace_file;
    const char *experience;
    long max_exits;
    long power_cut_lba;
    int power_cut_phase;
    const char *power_cut_copy;
    int trace;
    int no_timer;
    int raw_console;
    int trace_syscalls;
};

void cli_usage(const char *program);
int cli_parse_args(int argc, char **argv, struct cli_options *out);

#endif
