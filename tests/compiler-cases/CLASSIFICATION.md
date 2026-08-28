# Classification of -O2 sensitive cases

This file records the result of classifying each isolated compiler case as a
GCC bug, undefined behavior (UB) in the source, or an un-reproduced historical
hypothesis.

## buffer_freelist

* **Original source:** `fs/buffer.c` `getblk()` free-list walk.
* **Historical pattern:** `do { ... } while (tmp != free_list || (tmp = NULL));`
* **Reproduced on GCC 13.3?** No. The isolated case passes at `-O0`, `-O1`
  and `-O2` for both `x86_64` and `i386`.
* **Audit findings:** No strict-aliasing, sequence-point or UBSan diagnostics.
* **Classification:** **HISTORICAL_HYPOTHESIS / NOT_REPRODUCED**
* **Rationale:** The syntactic pattern is preserved from the 1991 source, but
  the claimed miscompilation does not manifest in the isolated reproduction on
  the tested toolchain. The symptom in the full kernel may require the original
  sleep points, global buffer-head state, or an older compiler version. The
  `-O1` workaround is safe and conservative.

## bitmap_inline_asm

* **Original source:** `fs/bitmap.c` `set_bit` / `clear_bit` / `find_first_zero`.
* **Historical pattern:** Inline-asm macros that modify memory through an
  operand declared input-only rather than read-write.
* **Reproduced on GCC 13.3?** Yes. The isolated case fails at `-O2` on
  `x86_64` while passing at `-O0`, `-O1` and on `i386`.
* **Audit findings:** UBSan does not flag the failure, because the issue is a
  violation of the inline-asm contract rather than a dynamic UB event.
* **Classification:** **UNDEFINED_BEHAVIOR (source contract violation)**
* **Rationale:** The `"m"` operand tells GCC that the asm reads memory but not
  that it writes it. At `-O2` GCC keeps a preloaded bitmap word in a register, so
  the subsequent C read observes the old value. A read-write memory operand,
  suitable clobber, or proper atomic built-in would express the side effect.
  This supports a source-contract violation in the hosted reduction, not a GCC
  bug or proof that `-O1` is necessary in the freestanding kernel.

## vsprintf_percent_s

* **Original source:** `kernel/vsprintf.c` `%s` conversion.
* **Historical pattern:** `s = va_arg(args, char *);`
* **Reproduced on GCC 13.3?** No. The isolated case passes at all optimization
  levels for both ABIs.
* **Audit findings:** No strict-aliasing, sequence-point or UBSan diagnostics.
* **Classification:** **HISTORICAL_HYPOTHESIS / NOT_REPRODUCED**
* **Rationale:** In isolation `va_arg(args, char *)` behaves correctly. The
  original symptom of reading the pointer from the wrong slot may depend on the
  full `printk` varargs calling path, stack alignment, or a different compiler
  version. The `-O1` workaround remains conservative.

## Summary

| Case | Classification | GCC bug? | Source UB? |
|------|----------------|----------|------------|
| `buffer_freelist` | HISTORICAL_HYPOTHESIS | unproven | no evidence |
| `bitmap_inline_asm` | UNDEFINED_BEHAVIOR | no | yes (asm contract) |
| `vsprintf_percent_s` | HISTORICAL_HYPOTHESIS | unproven | no evidence |

The versioned observations and tri-state machine classifications are published
in `datasets/compiler-cases/v1/`. Boolean `false` is not used for propositions
that the retained run merely fails to establish.
