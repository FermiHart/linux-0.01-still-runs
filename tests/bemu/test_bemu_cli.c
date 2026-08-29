/*
 * Author: F E R M I INFINITY H A R T <contact@fermihart.com>
 * SPDX-License-Identifier: Unlicense
 */

#include <stdio.h>
#include <string.h>

#include "../../bemu/cli.h"

static int failures;

static void check(int condition, const char *name)
{
    if (condition)
        printf("ok  %s\n", name);
    else {
        fprintf(stderr, "FAIL  %s\n", name);
        failures++;
    }
}

int main(void)
{
    struct cli_options options;
    char *defaults[] = { "bemu" };
    char *historical[] = { "bemu", "--experience", "1991" };
    char *custom[] = { "bemu", "--root", "custom.img", "--experience", "1991" };

    check(cli_parse_args(1, defaults, &options) == 0 &&
          strcmp(options.experience, "alive") == 0 &&
          strcmp(options.root, "build/root.img") == 0,
          "CLI defaults to alive root image");
    check(cli_parse_args(3, historical, &options) == 0 &&
          strcmp(options.experience, "1991") == 0 &&
          strcmp(options.root, "build/root-1991.img") == 0,
          "CLI selects historical root image");
    check(cli_parse_args(5, custom, &options) == 0 &&
          strcmp(options.root, "custom.img") == 0,
          "explicit root overrides profile default");

    if (failures) {
        fprintf(stderr, "%d CLI test(s) failed\n", failures);
        return 1;
    }
    return 0;
}
