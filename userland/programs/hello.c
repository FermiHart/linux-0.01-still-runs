/* hello.c — A C userland program for linux-0.01.
 *
 * Demonstrates using the minimal libc to perform syscalls.
 * Compile:
 *   x86_64-elf-gcc -m32 -march=i386 -ffreestanding -nostdlib -nostdinc \
 *       -Iuserland -c userland/programs/hello.c -o build/hello.o
 *   x86_64-elf-ld -m elf_i386 -nostdlib -Ttext 0 \
 *       build/crt0.o build/hello.o -o build/hello.elf
 *   x86_64-elf-objcopy -O binary build/hello.elf build/hello.bin
 *
 * Then mkimage wraps it as a.out ZMAGIC → /bin/hello
 */

#include "libc.h"

int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;
    write(1, "\033[36m", sizeof("\033[36m") - 1);   /* cyan */
    write(1, "\n", sizeof("\n") - 1);
    write(1, "  +--------------------------------------+\n",
          sizeof("  +--------------------------------------+\n") - 1);
    write(1, "  |  Hello from C userland!               |\n",
          sizeof("  |  Hello from C userland!               |\n") - 1);
    write(1, "  |  Linux 0.01 — Torvalds, 1991          |\n",
          sizeof("  |  Linux 0.01 — Torvalds, 1991          |\n") - 1);
    write(1, "  +--------------------------------------+\n",
          sizeof("  +--------------------------------------+\n") - 1);
    write(1, "\033[0m", sizeof("\033[0m") - 1);

    return 42;
}
