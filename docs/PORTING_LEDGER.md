# Porting Ledger

This ledger records every deliberate change to the historical Linux 0.01 core
(`init/`, `kernel/`, `mm/`, `fs/`, `lib/`, `include/`) and explains why it was
necessary. The upstream reference is `upstream/linux-0.01.tar.gz` with SHA-256
`24454f830cdb571e2c4ad15481119c43b3cafd48dd869a9b2945d1036d1dc68d`.

## Legend

| Field | Meaning |
|---|---|
| **Change** | What was modified |
| **Files** | Affected source files |
| **Category** | Hardware, Compiler, UndefinedBehavior, Time, Boot, Usability, Experience, HistoricalBug |
| **Evidence** | How we know the change is needed |
| **Test** | Test that exercises or validates the change |
| **Status** | PROVEN, QUALIFIED or UNDER_INVESTIGATION |

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
- **Category**: Compiler / UndefinedBehavior
- **Evidence**: At `-O2` the second `_open3(O_CREAT)` after a write panics.
  Whether this is a GCC optimization bug or UB in the 1991 idiom is under
  investigation (Waves 075–083).
- **Test**: `tests/test_shell.py` creates files repeatedly without panic.
- **Status**: UNDER_INVESTIGATION

### Bitmap `-O1` workaround

- **Change**: Compile `fs/bitmap.o` at `-O1` instead of `-O2`.
- **Files**: `fs/bitmap.c`, `Makefile`
- **Category**: Compiler / UndefinedBehavior
- **Evidence**: Same symptom class as `fs/buffer.c`; filesystem operations fail
  or panic at `-O2`.
- **Test**: Filesystem smoke tests pass.
- **Status**: UNDER_INVESTIGATION

### `vsprintf` `%s` handling

- **Change**: Compile `kernel/vsprintf.o` at `-O1` instead of `-O2`.
- **Files**: `kernel/vsprintf.c`, `Makefile`
- **Category**: Compiler / UndefinedBehavior
- **Evidence**: At `-O2` non-empty `%s` format strings read the pointer from the
  wrong slot and render garbage.
- **Test**: BBP status strings and shell `printk` output contain valid text.
- **Status**: UNDER_INVESTIGATION

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

## Classification summary

| Category | Count | Motivation |
|---|---|---|
| Compiler | 7 | Modern GCC rejects or mis-optimizes 1991 constructs |
| UndefinedBehavior | 2 | Code relies on behavior not guaranteed by the standard |
| Hardware | 4 | bEMU/KVM devices differ from 1991 PC assumptions |
| Time | 1 | CMOS century rollover |
| Usability | 2 | Without these the shell becomes unresponsive or unusable |
| Experience | 2 | Cosmetic/aesthetic choices that preserve or enhance feel |
| HistoricalBug | 0 | Intentional fixes of original Linux 0.01 bugs |

Counts are based on the ledger entries above. Entries marked QUALIFIED or
UNDER_INVESTIGATION may be reclassified after Waves 075–083.

## Pending entries

The following areas still need detailed ledger entries:

- Exact changes in `kernel/exit.c`, `kernel/fork.c`, `kernel/sys.c` for modern
  GCC and BBP.
- Exact changes in `fs/super.c` for root device and mount handling.
- Detailed provenance of `userland/shell.c`, `userland/crt0.S` and
  `userland/programs/hello.c` relative to any 1991 userland examples.

These will be filled in during Waves 012–015.
