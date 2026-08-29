/*
 * Author: F E R M I INFINITY H A R T <contact@fermihart.com>
 * SPDX-License-Identifier: Unlicense
 */

/* pathcheck.c — Minimal external command to verify PATH resolution and envp.
 *
 * Prints the first PATH= entry found in the environment vector passed by
 * execve(2).  Used by the shell smoke tests to confirm that bare command
 * lookup along $PATH works and that the kernel forwards envp to userland.
 */

#include "libc.h"

int main(int argc, char **argv, char **envp)
{
	char **p;

	(void)argc;
	(void)argv;

	for (p = envp; p && *p; p++) {
		if ((*p)[0] == 'P' && (*p)[1] == 'A' &&
		    (*p)[2] == 'T' && (*p)[3] == 'H' && (*p)[4] == '=') {
			printf(*p);
			printf("\n");
			return 0;
		}
	}

	printf("PATH not found\n");
	return 1;
}
