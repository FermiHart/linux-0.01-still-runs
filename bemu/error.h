#ifndef BEMU_ERROR_H
#define BEMU_ERROR_H

enum bemu_exit_code {
    BEMU_EXIT_OK = 0,
    BEMU_EXIT_RUNTIME = 1,
    BEMU_EXIT_CLI = 2,
    BEMU_EXIT_SIGNAL_BASE = 128,
};

#endif
