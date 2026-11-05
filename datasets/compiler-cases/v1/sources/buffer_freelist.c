/*
 * Minimal reproduction of the original Linux 0.01 getblk() free-list walk.
 *
 * The historical code used a do-while:
 *
 *     tmp = free_list;
 *     do {
 *         if (!tmp->b_count) {
 *             wait_on_buffer(tmp);
 *             if (!tmp->b_count)
 *                 break;
 *         }
 *         tmp = tmp->b_next_free;
 *     } while (tmp != free_list || (tmp = NULL));
 *     // Kids, don't try THIS at home. Magic.
 *
 * Semantics intended by the 1991 authors:
 *   - Walk the circular free list starting at free_list.
 *   - Return the first node whose ->used flag is zero.
 *   - If we complete the full cycle, set tmp to NULL to signal "none free".
 *
 * The `|| (tmp = NULL)` trick relies on the assignment being evaluated when
 * the left side of `||` becomes false, i.e. when tmp has gone all the way
 * around and is again equal to free_list.  Modern GCC at -O2 may drop the
 * assignment as a side-effect that is "unobservable" according to the
 * abstract machine, leaving tmp == free_list and making the caller believe
 * free_list itself is the chosen (or a valid) buffer.
 *
 * This file is a self-contained host program that builds a tiny circular list,
 * marks every node as used, and checks whether the loop correctly detects the
 * empty list.  With -O0 and -O1 the function returns NULL.  With aggressive
 * optimization the side-effect may be removed and the function returns a
 * non-NULL pointer, failing the assertion.
 */

#include <stdio.h>
#include <stdlib.h>
#include <assert.h>

struct node {
	int used;
	struct node *next;
};

static struct node n0 = { 1, NULL };
static struct node n1 = { 1, NULL };
static struct node n2 = { 1, NULL };
static struct node *free_list;

/* Keep the function in a separate compilation unit style, noinline, so the
 * optimizer cannot see the global list contents across the call boundary. */
static __attribute__((noinline))
struct node *get_node_original(void)
{
	struct node *tmp = free_list;

	do {
		if (!tmp->used)
			break;
		tmp = tmp->next;
	} while (tmp != free_list || (tmp = NULL));
	return tmp;
}

static void setup(void)
{
	n0.next = &n1;
	n1.next = &n2;
	n2.next = &n0;
	free_list = &n0;
}

int main(void)
{
	struct node *got;

	setup();
	got = get_node_original();
	if (got != NULL) {
		fprintf(stderr,
			"FAIL: expected NULL for a fully-used list, got %p\n",
			(void *)got);
		return 1;
	}

	/* Also verify a partially-free list works: n1 free, others used. */
	n1.used = 0;
	got = get_node_original();
	if (got != &n1) {
		fprintf(stderr,
			"FAIL: expected node n1 (%p), got %p\n",
			(void *)&n1, (void *)got);
		return 1;
	}

	puts("PASS: free-list loop behaves as intended");
	return 0;
}
