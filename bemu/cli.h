#ifndef BEMU_CLI_H
#define BEMU_CLI_H

struct cli_options {
    const char *kernel;
    const char *root;
    const char *script;
    const char *expect;
    const char *trace_file;
    long max_exits;
    int trace;
    int no_timer;
    int raw_console;
};

void cli_usage(const char *program);
int cli_parse_args(int argc, char **argv, struct cli_options *out);

#endif
