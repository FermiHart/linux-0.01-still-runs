# Compiler-case dataset

This directory contains minimal, self-contained reproductions of the three
`-O2` sensitive code patterns that the Linux 0.01 porting layer currently
works around by compiling specific objects at `-O1`:

| Case | Original file | Workaround | Pattern |
|------|---------------|------------|---------|
| `buffer_freelist` | `fs/buffer.c` | `fs/buffer.o` at `-O1` | Original `getblk()` free-list walk used `do { ... } while (tmp != free_list \|\| (tmp = NULL))`. |
| `bitmap_inline_asm` | `fs/bitmap.c` | `fs/bitmap.o` at `-O1` | `set_bit`/`clear_bit`/`find_first_zero` inline-asm macros lack a `"memory"` clobber. |
| `vsprintf_percent_s` | `kernel/vsprintf.c` | `kernel/vsprintf.o` at `-O1` | `va_arg(args, char *)` fetch for `%s` reportedly reads the wrong slot at `-O2`. |

## Running the harness

```bash
make -C tests/compiler-cases clean run   # compile and run all cases at -O0/-O1/-O2
make -C tests/compiler-cases report      # show the generated report
make -C tests/compiler-cases compare-assembly  # disassembly diffs
make -C tests/compiler-cases audit       # aliasing / sequence-point / UBSan audit
```

The harness builds each case for both `x86_64` and `i386` ABIs because the
original kernel is an i386 binary.

## What the reproductions demonstrate (GCC 13.3, Ubuntu 24.04)

* `bitmap_inline_asm` **fails at `-O2` on x86_64** because the compiler keeps
  the bitmap word in a register across the inline-asm `set_bit`.  Adding a
  `"memory"` clobber makes the write visible and the test passes.  This is a
  textbook undefined-behavior pattern in the inline-asm contract, not a GCC bug.

* `buffer_freelist` **passes at all optimization levels** with the current
  minimal reproduction.  The historical symptom may require the full kernel
  context (sleep points, global state, older GCC) or a slightly different
  idiom.  The reproduction is kept because it isolates the exact syntactic
  pattern from the original source.

* `vsprintf_percent_s` **passes at all optimization levels** with the current
  minimal reproduction.  The original symptom may depend on varargs layout in
  the full `printk` calling path or on an older compiler version.

## Files

* `Makefile` — build rules for all ABIs/optimization levels plus assembly,
  comparison and audit targets.
* `run.sh` — execute cases and write `build/report.txt`.
* `compare_asm.sh` — extract and diff the function under investigation.
* `audit.sh` — compile and run with strict-aliasing, sequence-point and UBSan
  diagnostics.
* `buffer_freelist.c`, `bitmap_inline_asm.c`, `vsprintf_percent_s.c` — the
  minimal reproductions.

## Output artifacts

All generated artifacts live under `build/` and are not committed:

* `build/report.txt` — pass/fail summary.
* `build/asm/*.asm` — disassembly of the target function.
* `build/asm/*.diff` — unified diffs between `-O0`, `-O1` and `-O2`.
* `build/audit.txt` — output of the audit passes.
