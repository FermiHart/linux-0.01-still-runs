<div align="center">

# linux-0.01-still-runs

**Linus Torvalds' 1991 kernel, booting on 2026 silicon.**

Not emulated. Not behind glass. Running.

<img src="docs/screenshots/01-boot-motd.png" alt="linux-0.01-still-runs booting through bEMU — kernel boot, full MOTD, PC-compatible 8x8 font, the year 2026" width="720"/>

[![CI](https://github.com/fermihart/linux-0.01-still-runs/actions/workflows/build.yml/badge.svg)](https://github.com/fermihart/linux-0.01-still-runs/actions/workflows/build.yml)
[![License: mixed](https://img.shields.io/badge/license-mixed-blue.svg)](LICENSE)
[![codename](https://img.shields.io/badge/codename-Vesica%20Piscis-purple)](#)
[![channel](https://img.shields.io/badge/channel-v0.1%20FOREVER-success)](#)

</div>

---

## A letter from 1991

There is a specific feeling that comes from booting an operating system written three and a half decades ago. It is not nostalgia — nostalgia implies distance, the safe view from behind glass. This is something else. This is the moment when the machine you built in 2026 loads a kernel whose ideas were typed out in a Helsinki bedroom, on a 386 with 33 megahertz and four megabytes of RAM, and *it works*.

Not works in the sense of a museum exhibit under rope and velvet. Works in the sense that you can type a command, create a directory, write a file, read it back, and feel the same feedback loop that Linus felt when he posted to comp.os.minix on that October morning:

> I'm doing a (free) operating system (just a hobby, won't be big and professional).

He was wrong about the scale. But he was right about the spirit.

This project exists to keep that spirit running. **Not frozen. Not emulated behind a glass pane. Running.** The original linux-0.01 source — every `sched.c`, every `buffer.c`, every hand-tuned assembly routine — is still here, still recognizable, still the heart of the machine. What we added is the thinnest possible bridge between that world and this one: a firmware-free KVM runner, a toolchain that speaks 2026 C while respecting 1991 conventions, and just enough runtime patches to make the thing boot without panicking on its own assumptions.

**Welcome to 1991. It still runs in 2026.**

---

## Quick start

The runtime requires Linux with `/dev/kvm`. Build and boot directly:

```bash
sudo apt install build-essential nasm python3

git clone https://github.com/fermihart/linux-0.01-still-runs
cd linux-0.01-still-runs
make toolchain   # verify/install missing build tools and KVM access
make boom        # clean + build + direct bEMU/KVM boot
```

Inside the booted system:

```sh
fermihart@linux01:/$ date              # Y2K-aware: shows real 2026
fermihart@linux01:/$ cal               # current month, today highlighted
fermihart@linux01:/$ fortune           # 15 quotes: Linus, Ritchie, Knuth...
fermihart@linux01:/$ linus             # the famous Aug 1991 comp.os.minix post
fermihart@linux01:/$ uptime            # seconds since CMOS boot
fermihart@linux01:/$ ps aux            # live task table from Linus' scheduler
fermihart@linux01:/$ cat /etc/motd     # the letter above, on the VGA console
```

---

## Screenshots

<div align="center">

| | |
|:---:|:---:|
| <img src="docs/screenshots/04-shell-commands.png" width="400"/><br/>**Interactive shell** — a 1991 Unix command suite | <img src="docs/screenshots/05-shell-hello-c.png" width="400"/><br/>**C userland** — `/bin/hello` built with the cross toolchain |
| <img src="docs/screenshots/02-build-splash.png" width="400"/><br/>**Cinematic build** — `make` with a Unicode splash | <img src="docs/screenshots/07-build-complete.png" width="400"/><br/>**Checksummed artifacts** — SHA-256-stamped on every build |
| <img src="docs/screenshots/08-build-stages.png" width="400"/><br/>**Build pipeline** — kernel → BBP-aware bEMU → Minix v1 rootfs forge | <img src="docs/screenshots/06-make-help.png" width="400"/><br/>**`make help`** — every target, self-documenting |

</div>

---

## Two-layer design

| Layer | Purpose | Status |
|-------|---------|--------|
| **Historical core** — `init/`, `kernel/`, `mm/`, `fs/`, `lib/`, `include/` | Original Linux 0.01 source from October 1991, patched only where modern hardware or modern GCC demand it | Recognizable line-for-line against the [kernel.org tarball](https://www.kernel.org/pub/linux/kernel/Historic/linux-0.01.tar.gz) |
| **Modern port** — `bemu/`, `bbp/`, `boot/`, `tools/`, `userland/`, `tests/`, `Makefile` | Direct KVM entry, BBP handoff, root-image generation, interactive shell, VGA 80×50 mode-set, bEMU smoke tests | New, minimal, written to feel period-correct where it touches the kernel |

This is therefore best described as **Linux 0.01 that runs today**, not a byte-for-byte preservation tree. For archaeology, compare against the official tarball. For experimentation, boot this repo.

---

## What you get

- **VGA 80×50 text mode** using an 8×8 PC-compatible character set derived from SeaBIOS VGA font data
- **Colored interactive shell** (`userland/shell.c`) with emacs line editing, tab completion, history, and ANSI colors on `ls`
- **1991 Unix command suite**: `date`, `cal`, `uptime`, `fortune`, `yes`, `true`, `false`, plus an Easter-egg `linus` that prints the original comp.os.minix announcement
- **Minix v1 filesystem** built by hand at image time (`tools/mkimage.c`), with `/etc/motd`, `/etc/passwd`, `/bin/{shell,hello,update}`, `/dev/tty0`
- **Firmware-free bEMU boot** — KVM enters `kernel.bin` at physical zero with no BIOS, UEFI, ISO, or bootloader
- **Real BBP handoff** — bEMU publishes CRC64-checksummed RAM, kernel, root-disk, and machine identity tags at physical `0xC0000`; CRC64 detects corruption but does not authenticate the producer
- **Real CMOS time** (Y2K rollover patched in `init/main.c` so `date` returns 2026 not 1970)
- **Automated validation**: build → direct KVM boot → run the full shell smoke suite

---

## Architecture

| Stage | Component | What it does |
|-------|-----------|--------------|
| 1 | `bemu/bemu_linux01.c` | Loads `kernel.bin` at phys 0, creates the BBP handoff, and provides the legacy devices through KVM |
| 2 | `boot/head.s` | Reprograms the PIC, initializes IDT/GDT and paging, zeros BSS, calls `main()` |
| 3 | `bbp/linux01_bbp.c` | Validates bEMU identity, memory, kernel, and root-disk tags |
| 4 | `init/main.c` | VGA 80×50 mode set → time → tty → traps → sched → buffer → fork-init |
| 5 | Linus' 1991 kernel | scheduler, fork, exec, Minix VFS, block/char devices, signals, pipes |
| 6 | Userland | `crt0.S` + interactive shell + `/bin/hello` demo |

Deep dive: [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Build / run / test

```bash
make help            # show every target with a one-line description
make all             # full build (kernel + root.img + bEMU), -Werror clean
make run             # build + direct KVM boot in the terminal
make run-headless    # alias for make run; bEMU is terminal-native
make boom            # clean + build + run — cinematic one-shot demo
make test            # boot + 53 shell commands + editor + large-rootfs tests
make doctor          # toolchain health check
make sizes           # kernel section sizes
make hash            # SHA-256 of all artifacts
```

Quick targeted shell test (≈ 30s per run):

```bash
python3 tests/qquick.py "date" --expect "2026"
python3 tests/qquick.py "ls"   --expect "bin"  --setup "cd etc"
```

Toolchain: `x86_64-elf-gcc` or native GCC with `-Wall -Werror -O2 -std=gnu89 -m32 -march=i386 -ffreestanding`; plus NASM, a host C compiler, Python 3, Linux KVM headers, and writable `/dev/kvm` for execution.

---

## Built-in commands

| Command | What it does |
|---------|--------------|
| `help` | List built-ins |
| `clear` | Clear the screen |
| `echo <text>` | Print text; supports `> file` and `>> file` |
| `cat <file>` | Read regular files |
| `ls` / `ls -la` | Coloured directory listing (blue dirs, green executables, yellow devices) |
| `cd <dir>` / `pwd` | Change directory + track cwd |
| `mkdir` / `rmdir` / `touch` / `rm [-rf]` | Session-local FS ops via the shell's VFS layer |
| `cp` / `mv` / `ln` | Copy, move, hard-link |
| `head` / `wc` / `grep` | Classic text inspection |
| `whoami` / `mount` / `df` / `ps aux` | System views over the live task/super-block state |
| `history` | Persistent across sessions in `/.sh_history` |
| `uname` / `uname -a` | Linux 0.01 `uname` syscall |
| **`date`** | Current date/time from CMOS RTC |
| **`cal`** | Month calendar, today highlighted |
| **`uptime`** | Seconds since boot, classic BSD load-average line |
| **`fortune`** | Random Unix wisdom (Linus, Ritchie, Thompson, Knuth, Dijkstra…) |
| **`yes [text]`** | Print `y` (or arg) 50× — terminating courtesy |
| **`true`** / **`false`** | Classic exit codes |
| **`linus`** | Easter egg: full text of the August 1991 comp.os.minix post |
| `hello` | Built-in banner |
| `/bin/hello` | Same banner via external `execve` |
| `halt` / `reboot` / `exit` | Clean shutdown / reboot / leave shell |

Tab completion: press `Tab` once to complete, twice to list matches in columns. Line editing: emacs bindings (`Ctrl-A/E/K/U/W/Y`, arrow keys for cursor + history).

---

## Notable fixes & curiosities

- **GCC -O2 mis-compiled `fs/buffer.c`'s free-list walk.** The original `while (tmp != free_list || (tmp=NULL))` trick discarded its side-effect on modern toolchains, causing the second `_open3(O_CREAT)` after any FS write to panic. Fixed by rewriting the loop AND dropping `fs/buffer.o`+`fs/bitmap.o` to `-O1`. Same class of Heisenbug as the existing `sys_ioctl` `volatile int ret` patch.
- **CMOS Y2K rollover.** `kernel_mktime` reads `tm_year` as years-since-1900; CMOS gives 2-digit year, so `26` meant 1926 → epoch went negative → `date` showed Jan 1 1970. Treat `< 70` as `20yy`.
- **Serial throughput.** UART was at 2400 baud with polled busy-wait; `printk` also routed every byte twice (`serial_puts` *and* `tty_write` → `con_write` → `serial_console_write`). At 26 commands the write_q saturated and the shell blocked. Bumped to 115200, dropped the duplicate path.
- **CP437 on VGA.** Original `con_write` filtered to bytes 32–126. Since we ship the full PC-compatible 8×8 font in plane 2, loosened the filter to let extended slots through — `∞` at `0xEC`, box-drawing chars, math symbols.

---

## Known limitations

| | |
|---|---|
| The supported build/test host is Linux KVM | bEMU requires Linux headers and writable `/dev/kvm`; no fallback backend is claimed |
| Runtime file creation in the shell is session-local (VFS-only); a kernel-side Minix allocator audit remains pending for true on-disk `mkdir`/`creat` | shell `mkdir/touch/rm` work; they just don't survive a reboot |
| External binary execution is explicit-by-path (`/bin/hello`). No `$PATH` resolution yet | by design — keeps the surface small |

---

## License

The historical kernel remains © 1991 Linus Torvalds under the original Linux
0.01 distribution terms. Modern files are under the Unlicense unless they
carry another identifier; bEMU and BBP are BSD-3-Clause. See [LICENSE](LICENSE)
for the complete notices and the pinned provenance of the public-domain VGA
font data.

---

<div align="center">

**F E R M I ∞ H A R T**

</div>
