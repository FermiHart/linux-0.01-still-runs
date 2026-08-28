/*
 * Minimal reproduction of fs/bitmap.c inline-asm bit operations.
 *
 * The original Linux 0.01 code defines set_bit / clear_bit / find_first_zero as
 * statement expressions containing inline __asm__ blocks.  None of these blocks
 * declares a "memory" clobber.  At -O2 GCC is therefore allowed to assume that
 * memory is unchanged across an asm statement that does not mention memory, and
 * may reorder or coalesce loads/stores around the bit operation.  In the real
 * kernel this causes new_block()'s getblk() result or subsequent buffer-head
 * fields to be observed inconsistently.
 *
 * This file simulates the pattern with a small bitmap and an explicit sequence
 * of "set bit" and "read back" operations.  Without a memory clobber the
 * compiler may keep the old value of the bitmap word in a register and the test
 * fails at -O2.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define set_bit(nr, addr) ({                    \
    register int res;                           \
    __asm__("btsl %2,%3\n\tsetb %%al"          \
        : "=a" (res)                           \
        : "0" (0), "r" (nr), "m" (*(addr)));  \
    res;                                        \
})

static unsigned long bitmap[2];

static __attribute__((noinline)) void use_bit(int n)
{
    unsigned long *word = &bitmap[n / 32];
    int bit = n & 31;
    int old;

    old = set_bit(bit, word);
    /* At this point the word in memory MUST have the bit set. */
    if (!(*word & (1UL << bit))) {
        fprintf(stderr,
            "FAIL: bit %d not visible after set_bit; old=%d word=0x%lx\n",
            n, old, *word);
        exit(1);
    }
}

int main(void)
{
    memset(bitmap, 0, sizeof(bitmap));

    use_bit(0);
    use_bit(31);
    use_bit(32);
    use_bit(63);

    puts("PASS: bit operations are visible after inline asm");
    return 0;
}
