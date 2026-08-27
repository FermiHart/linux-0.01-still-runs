# Porting Ledger

This ledger groups interpreted adaptations to the historical Linux 0.01 core
(`init/`, `kernel/`, `mm/`, `fs/`, `lib/`, `include/`) and explains their stated
purpose. The complete path-level delta, including unmatched ledger joins, is in
`datasets/patches/`. The upstream reference is `upstream/linux-0.01.tar.gz` with SHA-256
`24454f830cdb571e2c4ad15481119c43b3cafd48dd869a9b2945d1036d1dc68d`.

## Legend

| Field | Meaning |
|---|---|
| **Change** | What was modified |
| **Files** | Affected source files |
| **Category** | Hardware, Compiler, UndefinedBehavior, Time, Boot, Usability, Experience, HistoricalBug, HistoricalHypothesis |
| **Evidence** | How we know the change is needed |
| **Test** | Test that exercises or validates the change |
| **Status** | PROVEN, QUALIFIED, CORRECTED or UNDER_INVESTIGATION |

## Entries

### CMOS Y2K rollover

- **Change**: In `time_init()`, treat CMOS `tm_year < 70` as `20yy` by adding
  100 before calling `kernel_mktime()`.
- **Files**: `init/main.c`
- **Category**: Time
- **Evidence**: Without the patch `date` returns 1970 because `26` is interpreted as 1926.
- **Test**: `tests/test_shell.py` checks `date` output contains the current year.
- **Status**: PROVEN

### Syscall wrappers for modern GCC

- **Change**: Replace the `_syscall0()` macro definitions for `fork`, `pause`,
  `setup` and `sync` with explicit `int $0x80` inline wrappers. Modern GCC rejects
  the `static` redeclaration after the non-static prototypes in `unistd.h`.
- **Files**: `init/main.c`
- **Category**: Compiler
- **Evidence**: Build fails with "static declaration follows non-static declaration".
- **Test**: `make all` succeeds; kernel boots and forks init.
- **Status**: PROVEN

### VGA 80×50 text mode

- **Change**: Switch to the BIOS 8×8 font at boot so `con_init()` initializes
  50 rows instead of 25. Export `lines` and `attr` for assembly helpers. Add
  `copy_screen`, `copy_screen_down` and `clear_screen` helpers with proper
  clobbers and memory barriers.
- **Files**: `init/main.c`, `kernel/console.c`, `kernel/vga_text50.c`, `kernel/vga_font8x8.h`
- **Category**: Hardware / Experience
- **Evidence**: Original code hard-coded 25 lines; modern VGA text mode can
  select 8×8 font for 50 rows.
- **Test**: Visual/screenshot tests; boot messages fit without scrolling prematurely.
- **Status**: PROVEN

### Serial UART 115200 baud

- **Change**: Change UART divisor from `0x30` (2400 bps) to `0x01` (115200 bps)
  and add `serial_console_write()` for polled COM1 output.
- **Files**: `kernel/serial.c`
- **Category**: Hardware / Usability
- **Evidence**: At 2400 bps with printk routed through both serial and tty
  paths, the write queue saturated after ~25 shell commands and blocked.
- **Test**: `tests/test_shell.py` runs 50+ commands without serial backpressure.
- **Status**: PROVEN

### Console output duplication removal

- **Change**: Remove the duplicate printk path that sent every byte through both
  `serial_puts` and `tty_write` → `con_write` → `serial_console_write`.
- **Files**: `kernel/console.c`, `kernel/tty_io.c`
- **Category**: Hardware / Usability
- **Evidence**: Duplicate path doubled bytes sent to the UART and accelerated
  queue saturation.
- **Test**: Shell smoke tests remain responsive; no double characters on console.
- **Status**: PROVEN

### CP437 / extended VGA glyph filter

- **Change**: Relax `con_write()` filter from bytes 32–126 to allow extended
  glyphs such as `∞` (0xEC), box-drawing characters and math symbols.
- **Files**: `kernel/console.c`
- **Category**: Experience
- **Evidence**: The full 8×8 PC-compatible font is loaded; original filter hid
  the extended slots.
- **Test**: MOTD renders `∞` and box-drawing characters correctly.
- **Status**: PROVEN

### Buffer-cache free-list walk

- **Change**: Rewrite the free-list loop in `getblk()` to avoid the
  `while (tmp != free_list || (tmp=NULL))` idiom. Add null guard in
  `remove_from_hash_queue()`.
- **Files**: `fs/buffer.c`
- **Category**: Compiler / HistoricalHypothesis
- **Evidence**: At `-O2` the second `_open3(O_CREAT)` after a write panics.
  The isolated reproduction in `tests/compiler-cases/buffer_freelist.c` does not
  fail on GCC 13.3, so the historical claim of a GCC `-O2` miscompilation is
  currently not reproduced. The `-O1` workaround is retained as a defensive
  shield.
- **Test**: `tests/test_shell.py` creates files repeatedly without panic;
  `datasets/compiler-cases/v1/` retains six passing hosted reduction cells.
- **Status**: QUALIFIED → see `tests/compiler-cases/CLASSIFICATION.md`

### Bitmap `-O1` workaround

- **Change**: Compile `fs/bitmap.o` at `-O1` instead of `-O2`.
- **Files**: `fs/bitmap.c`, `Makefile`
- **Category**: UndefinedBehavior (inline-asm contract)
- **Evidence**: The `set_bit`/`clear_bit`/`find_first_zero` macros use inline asm
  that modifies a memory operand declared input-only. The hosted reduction fails
  at x86-64 `-O2` because a stale preloaded value is reused. This supports a
  source-contract violation in that cell, not a GCC bug or a necessity claim for
  the freestanding kernel.
- **Test**: Filesystem smoke tests pass;
  `datasets/compiler-cases/v1/` retains all six reduction cells and assembly.
- **Status**: CORRECTED → see `tests/compiler-cases/CLASSIFICATION.md`

### `vsprintf` `%s` handling

- **Change**: Compile `kernel/vsprintf.o` at `-O1` instead of `-O2`.
- **Files**: `kernel/vsprintf.c`, `Makefile`
- **Category**: Compiler / HistoricalHypothesis
- **Evidence**: The reported symptom of `-O2` reading the `%s` pointer from the
  wrong slot could not be reproduced in the isolated case
  `tests/compiler-cases/vsprintf_percent_s.c` on GCC 13.3. The `-O1` workaround
  is retained as a defensive shield.
- **Test**: BBP status strings and shell `printk` output contain valid text;
  `datasets/compiler-cases/v1/` retains six passing hosted reduction cells.
- **Status**: QUALIFIED → see `tests/compiler-cases/CLASSIFICATION.md`

### ATA PIO read helper and port macros

- **Change**: Add `read_abs_hd()` for polled two-sector reads, add memory
  clobbers to `port_read`/`port_write`, and add parentheses to the request
  sorting macro.
- **Files**: `kernel/hd.c`
- **Category**: Hardware / Compiler
- **Evidence**: bEMU exposes a CHS IDE disk; the original driver relied on BIOS
  geometry detection that is not available without firmware.
- **Test**: `tests/test_boot.py` reads partition table and mounts root.
- **Status**: PROVEN

### Colored diagnostic printk

- **Change**: Add ANSI color to partition-table and `sys_setup` messages.
- **Files**: `kernel/hd.c`
- **Category**: Experience
- **Evidence**: Improves readability of boot output without changing semantics.
- **Test**: Boot log contains colored "Partition table ok" and "sys_setup returning".
- **Status**: PROVEN

### `PIPE_HEAD` increment macro

- **Change**: Replace inline-assembly `INC_PIPE` macro with a pure C expression.
- **Files**: `include/linux/fs.h`
- **Category**: Compiler
- **Evidence**: Modern GCC handles the C expression identically and the assembly
  version is unnecessary.
- **Test**: Pipe tests in shell smoke suite.
- **Status**: PROVEN

### Filesystem patches for Minix v1 root image

- **Change**: Adjustments in `fs/super.c`, `fs/open.c`, `fs/exec.c`, `fs/stat.c`,
  `fs/namei.c`, `fs/char_dev.c`, `fs/pipe.c`, `fs/read_write.c`,
  `fs/tty_ioctl.c`, `fs/block_dev.c` to support the generated Minix v1 root
  image and device nodes.
- **Files**: `fs/*.c`
- **Category**: Hardware / Usability
- **Evidence**: The original driver set expected a different root device layout;
  the root image generated by `tools/mkimage.c` supplies `/dev/tty0`, `/bin/*`
  and `/etc/*`.
- **Test**: `tests/test_boot.py` mounts root; shell tests access files.
- **Status**: QUALIFIED

### `sys_ioctl` volatile return

- **Change**: Declare `ret` as `volatile int` in `sys_ioctl()`.
- **Files**: `fs/ioctl.c`
- **Category**: Compiler
- **Evidence**: Prevents an optimization-related Heisenbug in the tty ioctl path.
- **Test**: Terminal configuration commands in shell smoke suite.
- **Status**: PROVEN

### Memory-management compatibility

- **Change**: Adjustments in `mm/memory.c` and `mm/page.s` for modern GCC
  inline-assembly constraints and page-table handling.
- **Files**: `mm/memory.c`, `mm/page.s`
- **Category**: Compiler / Hardware
- **Evidence**: Build failures or paging faults without the constraints.
- **Test**: Boot and fork/exec smoke tests.
- **Status**: QUALIFIED

### Kernel assembly clobbers and constraints

- **Change**: Update inline assembly in `kernel/asm.s`, `kernel/system_call.s`,
  `kernel/keyboard.s`, `kernel/rs_io.s` for modern as/GCC constraints.
- **Files**: `kernel/*.s`
- **Category**: Compiler
- **Evidence**: Modern assembler rejects or misassembles some 1991 constructs.
- **Test**: Kernel builds and boots.
- **Status**: QUALIFIED

### Include header adjustments

- **Change**: Minor updates to `include/linux/*.h`, `include/asm/*.h`,
  `include/string.h`, `include/ctype.h`, `include/sys/wait.h` for modern
  toolchain compatibility and BBP integration.
- **Files**: `include/**/*.h`
- **Category**: Compiler / Experience
- **Evidence**: Type conflicts, missing prototypes, or BBP header requirements.
- **Test**: Full kernel and userland build.
- **Status**: QUALIFIED

### `lib/open.c` adjustment

- **Change**: Update `lib/open.c` for modern calling convention and BBP
  compatibility.
- **Files**: `lib/open.c`
- **Category**: Compiler
- **Evidence**: Build failure or warning without the change.
- **Test**: Userland C programs build and run.
- **Status**: QUALIFIED

### Validated experience environment bridge

- **Change**: Read the validated BBP experience selector in `init` and pass the
  matching `HOME` plus `EXPERIENCE` values to the shell.
- **Files**: `init/main.c`
- **Category**: Experience
- **Evidence**: A host-only Make or bEMU selector cannot change guest-visible
  identity without one minimal environment bridge after BBP validation.
- **Test**: `tests/test_experience.py` rejects mismatched images, boots the
  profiles, verifies their BBP command lines and real image files, and checks
  that bare `cd` returns to the selected HOME rather than the shell fallback.
- **Status**: PROVEN

## Test traceability

| Test | Ledger entries covered |
|---|---|
| `make all` | Syscall wrappers, VGA 50-row setup, include/header adjustments, memory-management compatibility, kernel assembly constraints |
| `tests/test_boot.py` | CMOS Y2K, serial UART, console duplication, ATA PIO, fs/buffer -O1 workaround, fs/bitmap -O1 workaround, filesystem Minix v1 patches, sys_ioctl volatile, pipe macro |
| `tests/test_shell.py` | CMOS Y2K, serial UART, console duplication, CP437 glyphs, fs/buffer workaround, filesystem patches, vsprintf %s workaround |
| `tests/test_experience.py` | Validated experience environment bridge |
| `tests/test_large_rootfs.py` | fs/buffer workaround, filesystem patches |
| `make sizes` | VGA 80×50 mode (kernel.elf sections) |

Every ledger entry above has a test field, but some fields are historical
descriptions rather than executable references. `datasets/patches/evidence_links.csv`
preserves that distinction and does not treat test source as retained run output.

## Classification summary

| Category | Count | Motivation |
|---|---|---|
| Compiler | 10 | Modern GCC rejects or exposes contracts in 1991 constructs |
| UndefinedBehavior | 1 | Code relies on behavior not guaranteed by the source/asm contract |
| Hardware | 6 | bEMU/KVM devices differ from 1991 PC assumptions |
| Time | 1 | CMOS century rollover |
| Usability | 3 | Without these the shell becomes unresponsive or unusable |
| Experience | 5 | Profile and presentation choices that preserve or enhance feel |
| HistoricalBug | 0 | Intentional fixes of original Linux 0.01 bugs |
| HistoricalHypothesis | 2 | Historical compiler explanations not reproduced in current reductions |

Counts are direct category memberships in the ledger entries above; one entry
may contribute to multiple categories.

## Pending entries

The Wave 108 path-level dataset exposes nine deltas without a ledger join:

- Exact changes in `kernel/exit.c`, `kernel/fork.c`, `kernel/panic.c`,
  `kernel/printk.c`, `kernel/sched.c`, `kernel/sys.c`, and `kernel/traps.c`.
- Exact changes in `lib/_exit.c` and the added `lib/sync.c`.
- Semantic attribution within broad `fs/*.c`, `kernel/*.s`, and
  `include/**/*.h` declarations.
- Detailed provenance of `userland/shell.c`, `userland/crt0.S` and
  `userland/programs/hello.c` relative to any 1991 userland examples remains
  outside the historical-core dataset.
