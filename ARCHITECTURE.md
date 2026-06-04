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
 ┌──────────┐    ┌────────────┐    ┌──────────┐    ┌──────────┐
 │ Firmware │───►│  Limine    │───►│bootstub  │───►│  head.s  │
 │ (BIOS/   │    │ multiboot2 │    │ .S       │    │startup_32│
 │  UEFI)   │    │ loader     │    │ @ 1 MiB  │    │ @ 0x0000 │
 └──────────┘    └────────────┘    └──────────┘    └──────────┘
                                         │
                                     memcpy kernel.bin
                                     to physical addr 0
                                         │
                                         ▼
                                    far jump to 0x0000
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
| 1 | `boot/bootstub.S` | `0x100000` | Limine entry; finds kernel.bin module, memcpy to phys 0 |
| 2 | `boot/bootstub.S` | `0x100000` | Reprogram 8259 PIC, install bridge GDT, far jump to 0 |
| 3 | `boot/head.s` | `0x000000` | Setup page directory/table, identity map 8 MiB |
| 4 | `boot/head.s` | `0x000000` | Setup IDT (all -> ignore_int), GDT (8 MiB limit) |
| 5 | `boot/head.s` | `0x000000` | Enable paging (CR0.PG=1), push args, call `main()` |
| 6 | `init/main.c` | — | `time_init()`, `tty_init()`, `trap_init()`, `sched_init()` |
| 7 | `init/main.c` | — | `buffer_init()`, `hd_init()`, `sti()`, `move_to_user_mode()` |
| 8 | `init/main.c` | — | `fork()` → `init()`, task 0 idle loop `pause()` |

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
         │  Buffer cache (end of kernel → 8 MiB)│
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
                       ├── [0] → phys 0x40000
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
- 80×25 characters, 16 colors

### Keyboard (`kernel/keyboard.s`)
- i8042 interrupt handler (IRQ 1)
- Scan code → ASCII translation table
- Handles shift, ctrl, alt, caps lock

### ATA Hard Disk (`kernel/hd.c`)
- PIO mode, interrupt-driven
- `hd_out()` sends command packets
- `rw_abs_hd()` translates LBA to CHS
- Block caching through `buffer.c`

### Serial (`kernel/serial.c` + `kernel/rs_io.s`)
- RS-232 at 0x3F8 (IRQ 4)
- Interrupt-driven transmit/receive
- 2400 baud, 8N1

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
├── boot/           ← Boot chain (Limine stubs, head.s, linker scripts)
├── init/           ← Kernel C entry: main(), init()
├── kernel/         ← Core subsystems (sched, syscalls, drivers, tty)
├── mm/             ← Memory management (page alloc, page fault)
├── fs/             ← Minix v1 filesystem (buffer, inode, namei, exec)
├── lib/            ← Library linked into kernel (string, syscall wrappers)
├── include/        ← Kernel headers (merged from 1991)
├── userland/       ← Userspace programs (sh.asm, update.asm, libc/)
├── tools/          ← Host tools (mkimage, bootmon)
├── gdb/            ← GDB pretty-printers
├── tests/          ← QEMU test harness
└── .github/        ← CI workflows
```

## Modernization Layer

The following files are **NOT** from Linus' 1991 tree — they form the 2026 adaptation layer:

| File | Purpose |
|------|---------|
| `boot/bootstub.S` | Limine multiboot2 entry → kernel relocation to phys 0 |
| `boot/bootstub.ld` | Linker script for bootstub at 1 MiB |
| `boot/kernel.ld` | Linker script for kernel at phys 0 |
| `boot/limine.conf` | Limine bootloader configuration |
| `tools/mkimage.c` | Minix v1 filesystem + MBR forger |
| `tools/bootmon.py` | VGA marker decoder and boot analyzer |
| `userland/sh.asm` | Minimal shell (NASM flat binary) |
| `userland/update.asm` | Sync daemon stub |
| `userland/libc/` | Userspace C library (syscall wrappers, crt0) |
| `Makefile` | Top-level build system (replaces original) |
| `Dockerfile` | Containerized build |
| `gdb/printers.py` | GDB pretty-printers for kernel structures |
| `tests/test_boot.py` | QEMU-based boot test harness |
| `.github/workflows/` | CI automation |

## References

- [Linux 0.01 original source (kernel.org)](https://www.kernel.org/pub/linux/kernel/Historic/)
- [Minix v1 filesystem specification](https://en.wikipedia.org/wiki/Minix_file_system)
- [Intel 80386 Programmer's Reference Manual (1986)](https://pdos.csail.mit.edu/6.828/2018/readings/i386/toc.htm)
- [Limine bootloader](https://github.com/limine-bootloader/limine)
- [a.out (ZMAGIC) format](https://en.wikipedia.org/wiki/A.out)
