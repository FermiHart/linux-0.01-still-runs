# Linux 0.01 Architecture Guide

> The kernel that booted the world — annotated for 2026 readers.

## Overview

Linux 0.01 is a **monolithic i386 kernel** released by Linus Torvalds in September 1991.
It implements a minimal UNIX-like operating system in ~10,000 lines of C and x86 assembly.

```
┌──────────────────────────────────────────────────────────┐
│                    USERSPACE (Ring 3)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │  /bin/sh  │  │/bin/upd. │  │  task N  │  ...          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │              │              │                      │
├───────┴──────────────┴──────────────┴──────────────────────┤
│                    KERNEL (Ring 0)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐ │
│  │ Process  │ │  Memory  │ │   File   │ │ Device Driver │ │
│  │ Manager  │ │ Manager  │ │  System  │ │  (HD, TTY)    │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───────┬───────┘ │
│       │             │            │                │         │
│  ┌────┴─────────────┴────────────┴────────────────┴───────┐│
│  │              System Call Dispatcher (int 0x80)         ││
│  └──────────────────────────┬─────────────────────────────┘│
│                             │                               │
│  ┌──────────────────────────┴─────────────────────────────┐│
│  │          Hardware Abstraction (IDT, GDT, TSS)          ││
│  └──────────────────────────┬─────────────────────────────┘│
├─────────────────────────────┴───────────────────────────────┤
│                     HARDWARE (i386)                          │
│   ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐ ┌──────────────┐  │
│   │ CPU  │ │ PIC  │ │ PIT  │ │  VGA   │ │  ATA HD      │  │
│   └──────┘ └──────┘ └──────┘ └────────┘ └──────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Boot Chain

```
                    linux-0.01-still-runs boot flow
 ┌──────────────┐    ┌──────────────┐    ┌──────────┐
 │ bEMU-NANO    │───►│ BBP handoff  │───►│  head.s  │
 │ KVM machine  │    │ @ 0xC0000    │    │startup_32│
 │ kernel @ 0   │    │ CRC64 tags   │    │ @ 0x0000 │
 └──────────────┘    └──────────────┘    └──────────┘
                                               │
                                      direct KVM entry at 0
                                               │
                                               ▼
 ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
 │ head.s   │───►│  main()  │───►│  init()  │───►│  /bin/sh │
 │ paging   │    │  inits   │    │  mounts  │    │  shell   │
 │ IDT/GDT  │    │  subsys  │    │  fork    │    │  loop    │
 └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### Stage Details

| Stage | File | Address | What happens |
|-------|------|---------|--------------|
| 1 | `bemu/memory.c`, `bemu/loader.c` | host | Allocate fixed 8 MiB RAM, validate the `L01KIMG1` length trailer, load only its payload at 0, and reject truncation, short reads or GDT/BBP overlap before KVM setup |
| 2 | `bemu/loader.c` | `0xC0000` | Produce CRC64-checksummed HHDM, memory-map, kernel-address, command-line and hypervisor tags |
| 3 | `boot/head.s` | `0x000000` | Remap 8259 PIC and setup page directory/table for 8 MiB |
| 4 | `boot/head.s` | `0x000000` | Setup IDT, GDT, enable paging, and call `main()` |
| 5 | `bbp/linux01_bbp.c` | `0xC0000` | Validate bEMU's untrusted BBP handoff and tag chain |
| 6 | `init/main.c` | — | Initialize devices, scheduler, and buffer cache |
| 7 | `init/main.c` | — | `sti()`, enter user mode, and `fork()` init |

The IDE root image is mapped separately by `bemu/ide.c`; it is not copied into
guest RAM. `bemu/kvm.c` receives already validated RAM and only registers it,
installs the bootstrap GDT, creates the VM/vCPU, and sets registers.
`kernel.bin` ends with an eight-byte `L01KIMG1` magic and an eight-byte
little-endian payload length. The trailer is a host artifact envelope, not part
of Linux memory; bEMU reports and loads only the preceding PA0 payload. Root
images use their exact 977/5/17 CHS byte length as the independent truncation
oracle before the writable mapping is created.
The IDE module also has a host-only test seam for one-shot ATA read/write errors
at a selected LBA; it is not exposed to the guest or command-line interface.
IDE writes are staged for one complete 512-byte sector before an atomic copy to
the mapped virtual medium. A separate host-only seam can stop the device at an
LBA-selected write-accept, payload-received, sector-committed or IRQ-requested
boundary. Tests materialize only committed sectors in disposable images; this
models bEMU's virtual-media state, not physical disk/cache durability.
The common IRQ bridge can similarly drop or defer one duplicate edge for a
selected IRQ. Duplicate replay waits for a completed KVM run, a low device line,
and clear IRR/ISR state in KVM's in-kernel 8259, including the slave cascade.
The keyboard module exposes only a host-test seam for Set-1 error bytes `0x00`
and `0xff`. Its terminal decoder carries escape state across polling boundaries;
non-TTY EOF emits a lone Escape key but discards incomplete CSI/SS3 input before
returning to the idle decoder state.
The guest power path emits an explicit one-byte intent on private port `0x8900`
before entering its `cli; hlt` loop. bEMU terminates normally only when that
request is followed by `KVM_MP_STATE_HALTED` with IF=0; the same CPU state without
a request, including kernel panic, is an error. HLT with IF=1 remains the normal
interruptible idle path. The reboot request ends the current process but does not
reset and recreate the VM in-process.
BBP corruption tests map a disposable copy of the exact 64 KiB handoff window
at `0xC0000` and call the production `bbp_linux01_init()` consumer. They repair
CRC64 after semantic mutations, leave it broken for integrity mutations, and
require bounded rejection of malformed headers, ranges, links, duplicate or
missing tags, and Linux 0.01-specific tag contents. No corrupt handoff enters
KVM or changes a canonical artifact.
Minix metadata fault tests operate offline on disposable image copies. They
never give a corrupt filesystem to the writable IDE mapping.

## Memory Layout (Physical)

```
0x000000 ┌──────────────────────────────────────┐
         │  Page Directory (pg_dir)             │ ← boot/head.s code overlays this
0x001000 ├──────────────────────────────────────┤
         │  Page Table 0 (pg0) — maps 0-4 MiB   │
0x002000 ├──────────────────────────────────────┤
         │  Page Table 1 (pg1) — maps 4-8 MiB   │
0x003000 ├──────────────────────────────────────┤
         │  (reserved)                          │
0x004000 ├──────────────────────────────────────┤
         │  Kernel .text / .rodata / .data      │
         │  Kernel .bss                         │
         ├──────────────────────────────────────┤
0x0C0000 │  BBP handoff (legacy reserved hole)  │
0x100000 ├──────────────────────────────────────┤
         │  Buffer cache / allocatable pages    │
0x800000 └──────────────────────────────────────┘
         │  (unmapped above 8 MiB)              │
```

## Process Management

### Task States

```
RUNNING (0) ◄────► ready to run on scheduler's list
INTERRUPTIBLE (1) ► sleeping, woken by signal or wake_up
UNINTERRUPTIBLE(2) ► sleeping, woken only by wake_up
ZOMBIE (3)        ► exited, waiting for parent's wait()
STOPPED (4)       ► stopped by signal
```

### Scheduler Algorithm

Round-robin with priority counters:

```c
// kernel/sched.c — simplified
void schedule(void) {
    for each task:
        if task->counter > best_counter → pick this task
    if all counters == 0:
        for each task:
            task->counter = task->priority  // reset
    switch_to(best_task)                    // hardware TSS switch
}
```

### Context Switch

Uses **hardware task switching** via `ljmp` to a TSS descriptor in the GDT.
The CPU saves/restores all registers automatically.

```
switch_to(n):
  ┌─►ljmp $TSS(n), $0    // CPU saves current TSS, loads TSS(n)
  │                       // CR3 reloaded → page table switch
  └─►iret returns to new task
```

## Memory Management

### Page Tables (Two-Level)

```
CR3 ──► Page Directory (pg_dir @ phys 0)
          │
          ├── [0] ──► Page Table 0 (pg0 @ phys 0x1000)
          │            ├── [0] → phys 0x00000 (4 KiB)
          │            ├── [1] → phys 0x01000
          │            └── ...
          │
          └── [1] ──► Page Table 1 (pg1 @ phys 0x2000)
                       ├── [0] → phys 0x400000
                       └── ...
```

### Page Fault Handling

```
do_no_page()  — Demand page: allocate a page, read from disk if needed
do_wp_page()  — Copy-on-write: duplicate page on write fault
                 (NOTE: fork() copies page tables, not pages yet)
```

## Filesystem: Minix v1

```
Block 0:  Boot block (zeros)
Block 1:  Superblock (magic 0x137F)
Block 2:  Inode bitmap (1 block = 8192 inodes tracked)
Block 3:  Zone bitmap  (1 block = 8192 zones tracked)
Block 4+: Inode table (32 inodes/block)
          └── Each inode: mode, owner, size, timestamps, 9x zone ptrs
Block N+: Data zones (1024 bytes each)
```

### Key Kernel Data Structures

```c
// include/linux/sched.h
struct task_struct {
    long state;              // -1 unrunnable, 0 runnable, >0 stopped
    long counter, priority;  // scheduling
    long signal;             // pending signal bitmap
    fn_ptr sig_fn[32];       // signal handlers
    long pid, father;        // process ID, parent PID
    struct file *filp[20];   // open file descriptors
    struct desc_struct ldt[3]; // per-task LDT
    struct tss_struct tss;   // hardware task state segment
};

// include/linux/fs.h
struct buffer_head {
    char *b_data;            // pointer to 1024-byte data block
    unsigned short b_dev;    // device number
    unsigned short b_blocknr;
    unsigned char b_dirt;    // dirty flag
    unsigned char b_count;   // reference count
    struct buffer_head *b_prev_free, *b_next_free;  // free list
};

// include/linux/fs.h
struct m_inode {
    unsigned short i_mode;   // file type + permissions
    unsigned short i_uid;
    unsigned long i_size;
    unsigned short i_zone[9]; // direct/indirect block pointers
    // ... in-memory fields
};
```

## Device Drivers

### VGA Console (`kernel/console.c`)
- Writes directly to framebuffer at `0xB8000` (VGA text mode)
- VT102 subset: cursor, scroll, ANSI escape sequences
- 80×50 characters, 16 colors

### Keyboard (`kernel/keyboard.s`)
- i8042 interrupt handler (IRQ 1)
- Scan code → ASCII translation table
- Handles shift, ctrl, alt, caps lock

### ATA Hard Disk (`kernel/hd.c`)
- PIO mode; bounded polling reads and interrupt-driven writes
- `hd_out()` sends command packets
- `rw_abs_hd()` translates LBA to CHS
- Block caching through `buffer.c`

### Serial (`kernel/serial.c` + `kernel/rs_io.s`)
- RS-232 at 0x3F8 (IRQ 4)
- Interrupt-driven transmit/receive
- 115200 baud, 8N1

## System Calls (67 total)

Dispatch via `int $0x80` → `kernel/system_call.s` → `include/linux/sys.h` table.

| # | Name | # | Name | # | Name |
|---|------|---|------|---|------|
| 1 | exit | 2 | fork | 3 | read |
| 4 | write | 5 | open | 6 | close |
| 7 | waitpid | 8 | creat | 9 | link |
| 10| unlink | 11| execve | 12| chdir |
| 13| time | 14| mknod | 15| chmod |
| 16| chown | 17| break | 18| stat |
| 19| lseek | 20| getpid | 21| mount |
| 22| umount | 23| setuid | 24| getuid |
| 25| stime | 26| ptrace | 27| alarm |
| 28| fstat | 29| pause | 30| utime |
| 31| stty | 32| gtty | 33| access |
| 34| nice | 35| ftime | 36| sync |
| 37| kill | 38| rename | 39| mkdir |
| 40| rmdir | 41| dup | 42| pipe |
| 43| times | 44| prof | 45| brk |
| 46| setgid | 47| getgid | 48| signal |
| 49| geteuid | 50| getegid | 51| acct |
| 52| phys | 53| lock | 54| ioctl |
| 55| fcntl | 56| mpx | 57| setpgid |
| 58| ulimit | 59| uname | 60| setup |

## Source Tree Map

```
linux-0.01-still-runs/
├── bemu/           ← Firmware-free KVM machine and device models
├── bbp/            ← CRC-checksummed bEMU-to-kernel handoff protocol
├── boot/           ← Direct kernel entry and linker script
├── init/           ← Kernel C entry: main(), init()
├── kernel/         ← Core subsystems (sched, syscalls, drivers, tty)
├── mm/             ← Memory management (page alloc, page fault)
├── fs/             ← Minix v1 filesystem (buffer, inode, namei, exec)
├── lib/            ← Library linked into kernel (string, syscall wrappers)
├── include/        ← Kernel headers (merged from 1991)
├── userland/       ← Userspace programs (sh.asm, update.asm, libc/)
├── tools/          ← Host tools (root image and toolchain setup)
├── gdb/            ← GDB pretty-printers
├── tests/          ← bEMU/KVM test harness
└── .github/        ← CI workflows
```

## Modernization Layer

The following files are **NOT** from Linus' 1991 tree — they form the 2026 adaptation layer:

| File | Purpose |
|------|---------|
| `bemu/bemu_linux01.c` | Direct KVM runner and Linux 0.01 device model |
| `bbp/linux01_bbp.c` | Kernel-side validation of bEMU's BBP handoff |
| `boot/kernel.ld` | Linker script for kernel at phys 0 |
| `tools/mkimage.c` | Minix v1 filesystem + MBR forger |
| `userland/sh.asm` | Minimal shell (NASM flat binary) |
| `userland/update.asm` | Sync daemon stub |
| `userland/libc.h`, `userland/crt0.S` | Userspace C syscall wrappers and runtime entry |
| `Makefile` | Top-level build system (replaces original) |
| `Dockerfile` | Containerized build |
| `gdb/printers.py` | GDB pretty-printers for kernel structures |
| `tests/test_boot.py` | bEMU-based boot test harness |
| `.github/workflows/` | CI automation |

## References

- [Linux 0.01 original source (kernel.org)](https://www.kernel.org/pub/linux/kernel/Historic/)
- [Minix v1 filesystem specification](https://en.wikipedia.org/wiki/Minix_file_system)
- [Intel 80386 Programmer's Reference Manual (1986)](https://pdos.csail.mit.edu/6.828/2018/readings/i386/toc.htm)
- [Linux KVM API](https://docs.kernel.org/virt/kvm/api.html)
- [a.out (ZMAGIC) format](https://en.wikipedia.org/wiki/A.out)
