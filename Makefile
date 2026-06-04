# ════════════════════════════════════════════════════════════════════════════
#
#   linux-0.01-still-runs  —  Makefile  [ Vesica Piscis Edition ]
#
#   Author    : F E R M I ∞ H A R T  <contact@fermihart.com>
#   Subject   : Linus Torvalds' first kernel (1991) booting on 2026 iron
#   Codename  : Vesica Piscis      Channel: v0.1 FOREVER
#   License   : FHCL draft / Unlicense fallback
#
#   First time?  →  make help
#   Show off?    →  make boom        (clean + build + launch QEMU)
#   Daily work?  →  make run         (build incrementally + run)
#
# ════════════════════════════════════════════════════════════════════════════

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ──────────────────────────────────────────────── identity ──────────────────
CODENAME   := Vesica Piscis
VERSION    := 0.01
RELEASE    := $(CODENAME)-$(VERSION)
AUTHOR     := F E R M I ∞ H A R T
EMAIL      := contact@fermihart.com
BUILD_DATE := $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
BUILD_HOST := $(shell hostname -s 2>/dev/null || hostname)
GIT_REV    := $(shell git rev-parse --short HEAD 2>/dev/null || echo "no-git")
GIT_DIRTY  := $(shell git diff --quiet 2>/dev/null && printf ' ' || printf '★')
UNAME_S    := $(shell uname -s)

# ──────────────────────────────────────────────── toolchain ─────────────────
PREFIX     := x86_64-elf-
CC         := $(PREFIX)gcc
AS         := $(PREFIX)as
LD         := $(PREFIX)ld
OBJCOPY    := $(PREFIX)objcopy
OBJDUMP    := $(PREFIX)objdump
NM         := $(PREFIX)nm
NASM       := nasm
QEMU       := qemu-system-i386
XORRISO    := xorriso
# Limine bootloader. Auto-detected so the build never hard-depends on a hand-
# populated /tmp dir. Resolution order (first hit wins; override on the CLI with
# `make LIMINE_DIR=/path`):
#   1. legacy /tmp/limine-src build dir (if it still has the artifacts)
#   2. Homebrew/system data dir (/usr/local or /opt/homebrew share/limine)
# LIMINE_BIN is resolved separately because brew ships the data in share/ but the
# `limine` executable in bin/ (PATH).
LIMINE_DIR ?= $(shell \
  if [ -f /tmp/limine-src/limine-bios-cd.bin ]; then echo /tmp/limine-src; \
  elif [ -f /usr/local/share/limine/limine-bios-cd.bin ]; then echo /usr/local/share/limine; \
  elif [ -f /opt/homebrew/share/limine/limine-bios-cd.bin ]; then echo /opt/homebrew/share/limine; \
  else echo /tmp/limine-src; fi)
LIMINE_BIN ?= $(shell command -v limine 2>/dev/null || echo $(LIMINE_DIR)/limine)

# ──────────────────────────────────────────────── flags ─────────────────────
COMMON_FLAGS = -m32 -march=i386 \
               -ffreestanding -nostdinc -fno-pie -fno-pic \
               -fno-stack-protector -fno-asynchronous-unwind-tables \
               -fno-builtin -fleading-underscore -fno-omit-frame-pointer \
               -mpreferred-stack-boundary=2 \
               -Wall -Werror -O2

CFLAGS  := $(COMMON_FLAGS) -std=gnu89 -Iinclude
ASFLAGS := --32
LDFLAGS := -m elf_i386 -nostdlib -z noexecstack -z max-page-size=0x1000 --no-warn-rwx-segments

BUILD := build

# ──────────────────────────────────────────────── object lists ──────────────
KERNEL_OBJS := \
    kernel/sched.o kernel/system_call.o kernel/traps.o kernel/asm.o \
    kernel/fork.o kernel/panic.o kernel/printk.o kernel/vsprintf.o \
    kernel/tty_io.o kernel/console.o kernel/keyboard.o kernel/rs_io.o \
    kernel/hd.o kernel/sys.o kernel/exit.o kernel/serial.o kernel/mktime.o \
    kernel/vga_text50.o

MM_OBJS := mm/memory.o mm/page.o

FS_OBJS := \
    fs/open.o fs/read_write.o fs/inode.o fs/file_table.o fs/buffer.o \
    fs/super.o fs/block_dev.o fs/char_dev.o fs/file_dev.o fs/stat.o \
    fs/exec.o fs/pipe.o fs/namei.o fs/bitmap.o fs/fcntl.o fs/ioctl.o \
    fs/tty_ioctl.o fs/truncate.o

LIB_OBJS := \
    lib/ctype.o lib/_exit.o lib/open.o lib/close.o lib/errno.o \
    lib/write.o lib/dup.o lib/setsid.o lib/execve.o lib/wait.o lib/string.o

INIT_OBJS := init/main.o
HEAD_OBJ  := boot/head.o

# ── Bear Boot Protocol (BBP) — native linux-0.01 port ────────────────────────
# Additive, non-fatal CRC-sealed boot-handoff layer. Lives entirely in bbp/.
# The BBP core REQUIRES C99+ (for-initializer declarations), but the 1991
# kernel builds -std=gnu89; so the BBP objects get their OWN -std=gnu11 while
# keeping every OTHER kernel flag — crucially -fleading-underscore, so the glue
# resolves _printk / _panic exactly like the rest of the kernel. See bbp/.
BBP_OBJS := \
    bbp/bbp_kernel.o bbp/bbp_build.o bbp/osif.o bbp/adapter.o bbp/linux01_bbp.o

ALL_OBJS := $(HEAD_OBJ) $(INIT_OBJS) $(KERNEL_OBJS) $(MM_OBJS) $(FS_OBJS) $(LIB_OBJS) $(BBP_OBJS)

# ──────────────────────────────────────────────── ANSI palette ──────────────
ifneq ($(NO_COLOR),)
CR  :=
CB  :=
CD  :=
CC1 :=
CM  :=
CG  :=
CY  :=
CRD :=
CGY :=
CP  :=
CWH :=
else
ESC := \033
CR  := $(ESC)[0m
CB  := $(ESC)[1m
CD  := $(ESC)[2m
CC1 := $(ESC)[38;5;51m
CM  := $(ESC)[38;5;207m
CG  := $(ESC)[38;5;83m
CY  := $(ESC)[38;5;221m
CRD := $(ESC)[38;5;203m
CGY := $(ESC)[38;5;240m
CP  := $(ESC)[38;5;141m
CWH := $(ESC)[38;5;255m
endif

# Unicode glyphs
G_OK   := ✓
G_NO   := ✗
G_ARR  := ▶
G_INF  := ◢
G_DOT  := •
G_INF8 := ∞

# ──────────────────────────────────────────────── splash macro ──────────────
define SPLASH
	@printf '$(CC1)╔══════════════════════════════════════════════════════════════════════════╗$(CR)\n'
	@printf '$(CC1)║$(CR)                                                                          $(CC1)║$(CR)\n'
	@printf '$(CC1)║$(CR)   $(CB)$(CM)F$(CR) $(CB)$(CM)E$(CR) $(CB)$(CM)R$(CR) $(CB)$(CM)M$(CR) $(CB)$(CM)I$(CR)    $(CY)$(G_INF8)$(CR)    $(CB)$(CM)H$(CR) $(CB)$(CM)A$(CR) $(CB)$(CM)R$(CR) $(CB)$(CM)T$(CR)                                              $(CC1)║$(CR)\n'
	@printf '$(CC1)║$(CR)                                                                          $(CC1)║$(CR)\n'
	@printf '$(CC1)║$(CR)   $(CWH)linux-0.01$(CR) $(CGY)·$(CR) $(CG)Linus Torvalds, 1991$(CR) $(CGY)→$(CR) $(CG)booting on 2026 iron$(CR)               $(CC1)║$(CR)\n'
	@printf '$(CC1)║$(CR)   $(CGY)codename$(CR) $(CY)$(RELEASE)$(GIT_DIRTY)$(CR) $(CGY)·$(CR) $(CGY)rev$(CR) $(CP)$(GIT_REV)$(CR) $(CGY)·$(CR) $(CGY)$(BUILD_DATE)$(CR)      $(CC1)║$(CR)\n'
	@printf '$(CC1)║$(CR)                                                                          $(CC1)║$(CR)\n'
	@printf '$(CC1)╚══════════════════════════════════════════════════════════════════════════╝$(CR)\n'
endef

define STAGE
	@printf '\n$(CC1)$(G_ARR)$(CR) $(CB)$(CWH)stage %s$(CR) $(CGY)·$(CR) $(CY)%s$(CR)\n' "$(1)" "$(2)"
endef

define STEP
	@printf '  $(CGY)$(G_DOT)$(CR) %s\n' "$(1)"
endef

define OK
	@printf '  $(CG)$(G_OK)$(CR) $(CGY)%s$(CR)\n' "$(1)"
endef

# ──────────────────────────────────────────────── phony decls ───────────────
.PHONY: help all clean deepclean run run-uefi run-debug run-headless run-monitor \
        iso kernel image dirs boom doctor info sizes symbols hash tree stats \
        audit journey watch ci backup logs screenshot replay banner \
        test test-quick test-shell test-large-rootfs bootmon gdb

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              MAIN BUILD                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

all: banner $(BUILD)/linux-0.01.iso $(BUILD)/root.img
	@$(call _summary)

banner:
	$(SPLASH)

dirs:
	@mkdir -p $(BUILD) $(BUILD)/iso_root

%.o: %.c
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s\n' "$<" "$@"
	@$(CC) $(CFLAGS) -c -o $@ $<

# fs/buffer.c + fs/bitmap.c: -O2 mis-compiles the buffer-cache walk and
# new_block's getblk result handling on modern GCC (Heisenbug — masked by
# any printk in the hot path, repros only with debug-free -O2). Drop to
# -O1 here only. Same class as the sys_ioctl `volatile int ret` fix.
fs/buffer.o: fs/buffer.c
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s $(CGY)[-O1 heisenbug]$(CR)\n' "$<" "$@"
	@$(CC) $(filter-out -O2,$(CFLAGS)) -O1 -c -o $@ $<

fs/bitmap.o: fs/bitmap.c
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s $(CGY)[-O1 heisenbug]$(CR)\n' "$<" "$@"
	@$(CC) $(filter-out -O2,$(CFLAGS)) -O1 -c -o $@ $<

# kernel/vsprintf.c: -O2 miscompiles the `%s` case (va_arg(char*) fetch) on
# modern GCC — a non-empty %s renders garbage (the pointer is read off by a
# slot), while %x/%c/%d are fine. Same heisenbug class as fs/buffer.o and
# fs/bitmap.o above. The 1991 boot path only ever passed empty strings to %s
# (hd.c "Partition table%s"), so this latent bug went unseen until the BBP
# adapter printed a real status string. Drop to -O1 here only.
kernel/vsprintf.o: kernel/vsprintf.c
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s $(CGY)[-O1 %%s heisenbug]$(CR)\n' "$<" "$@"
	@$(CC) $(filter-out -O2,$(CFLAGS)) -O1 -c -o $@ $<

# ── BBP objects: same kernel flags (incl. -fleading-underscore so _printk /
# _panic resolve), but -std=gnu11 (the core uses C99 for-initializer
# declarations) plus the BBP core + compat-shim include paths.
# -DBBP_L01_HIGH_MEMORY is pulled live from include/linux/config.h so the glue's
# RAM model always matches the kernel ceiling. The active #define is the one not
# guarded out; LINUS_HD selects 0x800000. tools/bbp_highmem.sh asks the C
# preprocessor for the active value (a bare $(shell awk ...) trips make's paren
# counting on the (0x...) literal, hence the helper script).
BBP_HIGH_MEMORY := $(shell sh tools/bbp_highmem.sh)
BBP_CFLAGS := $(filter-out -std=gnu89,$(COMMON_FLAGS)) -std=gnu11 \
              -Ibbp/include -Ibbp/compat -Iinclude \
              -DBBP_L01_HIGH_MEMORY=$(BBP_HIGH_MEMORY)

# Each BBP object is pinned explicitly: GNU make 3.81 (macOS bundled) does not
# reliably prefer the shorter-stem `bbp/%.o` over the generic `%.o: %.c`, so a
# pattern rule alone could be shadowed and silently compile with the wrong
# (gnu89, no-BBP-include) flags. Explicit targets guarantee BBP_CFLAGS.
#
# Header deps are listed explicitly: this Makefile predates -MMD auto-deps, so
# without these, editing a BBP header would not rebuild the objects that include
# it (silent stale build). BBP_HDRS is every header the BBP TUs can pull.
BBP_HDRS := bbp/include/bbp/bbp.h bbp/include/bbp/bbp_crc64.h \
            bbp/include/bbp/bbp_osif.h bbp/bbp_kernel.h bbp/bbp_build.h \
            bbp/osif.h bbp/adapter.h bbp/linux01_bbp.h \
            bbp/compat/stdint.h bbp/compat/stddef.h

bbp/bbp_kernel.o:  bbp/bbp_kernel.c $(BBP_HDRS)
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s $(CGY)[bbp gnu11]$(CR)\n' "$<" "$@"
	@$(CC) $(BBP_CFLAGS) -c -o $@ $<
bbp/bbp_build.o:   bbp/bbp_build.c $(BBP_HDRS)
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s $(CGY)[bbp gnu11]$(CR)\n' "$<" "$@"
	@$(CC) $(BBP_CFLAGS) -c -o $@ $<
bbp/osif.o:        bbp/osif.c $(BBP_HDRS)
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s $(CGY)[bbp gnu11]$(CR)\n' "$<" "$@"
	@$(CC) $(BBP_CFLAGS) -c -o $@ $<
bbp/adapter.o:     bbp/adapter.c $(BBP_HDRS)
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s $(CGY)[bbp gnu11]$(CR)\n' "$<" "$@"
	@$(CC) $(BBP_CFLAGS) -c -o $@ $<
bbp/linux01_bbp.o: bbp/linux01_bbp.c $(BBP_HDRS)
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s $(CGY)[bbp gnu11]$(CR)\n' "$<" "$@"
	@$(CC) $(BBP_CFLAGS) -c -o $@ $<

# init/main.c includes bbp/linux01_bbp.h (the call site), which pulls <bbp/bbp.h>.
# It still compiles -std=gnu89 like the rest of the kernel (the BBP headers are
# gnu89-clean), it just needs the BBP header search paths. Additive override.
init/main.o: init/main.c bbp/linux01_bbp.h bbp/bbp_kernel.h bbp/include/bbp/bbp.h
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s\n' "$<" "$@"
	@$(CC) $(CFLAGS) -Ibbp -Ibbp/include -Ibbp/compat -c -o $@ $<

%.o: %.s
	@printf '  $(CGY)as  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s\n' "$<" "$@"
	@$(AS) $(ASFLAGS) -o $@ $<

%.o: %.S
	@printf '  $(CGY)cpp $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s\n' "$<" "$@"
	@$(CC) $(CFLAGS) -c -o $@ $<

$(BUILD)/kernel.elf: $(ALL_OBJS) boot/kernel.ld | dirs
	$(call STAGE,5/10,linking kernel.elf @ phys 0x00000000)
	@$(LD) $(LDFLAGS) -T boot/kernel.ld -o $@ $(ALL_OBJS) 2>&1 | sed 's/^/    /'
	$(call OK,kernel.elf ready)

$(BUILD)/kernel.bin: $(BUILD)/kernel.elf
	@$(OBJCOPY) -O binary $< $@
	@printf '  $(CC1)$(G_INF)$(CR) %-22s $(CY)%s$(CR) bytes\n' \
	  "kernel.bin" "$$(stat -f%z $@ 2>/dev/null || stat -c%s $@)"

$(BUILD)/bootstub.elf: boot/bootstub.o boot/bootstub.ld | dirs
	$(call STAGE,6/10,linking bootstub.elf @ phys 0x00100000)
	@$(LD) $(LDFLAGS) -T boot/bootstub.ld -o $@ boot/bootstub.o
	$(call OK,bootstub.elf ready)

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              USERLAND                                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

$(BUILD)/sh.bin: userland/sh.asm | dirs
	$(call STEP,assembling userland/sh.asm (mini-ash))
	@$(NASM) -f bin $< -o $@

$(BUILD)/update.bin: userland/update.asm | dirs
	$(call STEP,assembling userland/update.asm (sync daemon))
	@$(NASM) -f bin $< -o $@

# ── Userland C programs ───────────────────────────────────────────

$(BUILD)/crt0.o: userland/crt0.S | dirs
	$(call STEP,assembling userland/crt0.S (C runtime))
	@$(AS) $(ASFLAGS) -o $@ $<

$(BUILD)/hello.bin: userland/programs/hello.c $(BUILD)/crt0.o | dirs
	$(call STEP,compiling userland/programs/hello.c (C userland demo))
	@$(CC) $(CFLAGS) -Iuserland -c userland/programs/hello.c -o $(BUILD)/hello.o
	@$(LD) $(LDFLAGS) -Ttext 0 -e _entry $(BUILD)/crt0.o $(BUILD)/hello.o -o $(BUILD)/hello.elf
	@$(OBJCOPY) -O binary $(BUILD)/hello.elf $(BUILD)/hello.bin
	@printf '  $(CC1)$(G_INF)$(CR) %-22s $(CY)%s$(CR) bytes\n' \
	  "hello.bin" "$$(stat -f%z $(BUILD)/hello.bin 2>/dev/null || stat -c%s $(BUILD)/hello.bin)"

$(BUILD)/shell.bin: userland/shell.c $(BUILD)/crt0.o | dirs
	$(call STEP,compiling userland/shell.c (interactive shell))
	@$(CC) $(filter-out -O2,$(CFLAGS)) -Os -Iuserland -c userland/shell.c -o $(BUILD)/shell.o
	@$(LD) $(LDFLAGS) -Ttext 0 -e _entry $(BUILD)/crt0.o $(BUILD)/shell.o -o $(BUILD)/shell.elf
	@$(OBJCOPY) -O binary $(BUILD)/shell.elf $(BUILD)/shell.bin
	@printf '  $(CC1)$(G_INF)$(CR) %-22s $(CY)%s$(CR) bytes\n' \
	  "shell.bin" "$$(stat -f%z $(BUILD)/shell.bin 2>/dev/null || stat -c%s $(BUILD)/shell.bin)"

# ── Host tools ────────────────────────────────────────────────────

$(BUILD)/mkimage: tools/mkimage.c | dirs
	$(call STEP,building tools/mkimage (Minix v1 + MBR forge))
	@cc -O2 -Wno-format -o $@ $<

# Collect all userland binaries (ASM + C)
USERLAND_BINS := $(BUILD)/shell.bin $(BUILD)/update.bin $(BUILD)/hello.bin

$(BUILD)/root.img: $(BUILD)/mkimage $(USERLAND_BINS)
	$(call STAGE,7/10,forging Minix v1 root filesystem)
	@$(BUILD)/mkimage $@ $(BUILD)/shell.bin $(BUILD)/update.bin $(BUILD)/hello.bin 2>&1 | sed 's/^/    /'
	$(call OK,root.img forged)

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                                ISO                                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

$(BUILD)/linux-0.01.iso: $(BUILD)/bootstub.elf $(BUILD)/kernel.bin boot/limine.conf
	$(call STAGE,8/10,assembling bootable ISO (BIOS + UEFI))
	@rm -rf $(BUILD)/iso_root
	@mkdir -p $(BUILD)/iso_root/boot/limine $(BUILD)/iso_root/EFI/BOOT
	@cp $(BUILD)/bootstub.elf       $(BUILD)/iso_root/boot/kernel.elf
	@cp $(BUILD)/kernel.bin         $(BUILD)/iso_root/boot/linus.bin
	@cp boot/limine.conf            $(BUILD)/iso_root/boot/limine/
	@cp $(LIMINE_DIR)/limine-bios.sys    $(BUILD)/iso_root/boot/limine/
	@cp $(LIMINE_DIR)/limine-bios-cd.bin $(BUILD)/iso_root/boot/limine/
	@cp $(LIMINE_DIR)/limine-uefi-cd.bin $(BUILD)/iso_root/boot/limine/
	@cp $(LIMINE_DIR)/BOOTX64.EFI        $(BUILD)/iso_root/EFI/BOOT/
	@$(XORRISO) -as mkisofs -b boot/limine/limine-bios-cd.bin \
	  -no-emul-boot -boot-load-size 4 -boot-info-table \
	  --efi-boot boot/limine/limine-uefi-cd.bin \
	  -efi-boot-part --efi-boot-image --protective-msdos-label \
	  $(BUILD)/iso_root -o $@ 2>&1 | tail -3 | sed 's/^/    /'
	@$(LIMINE_BIN) bios-install $@ 2>&1 | tail -2 | sed 's/^/    /'
	$(call OK,ISO sealed (BIOS+UEFI dual-protocol))

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              RUN TARGETS                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

ifeq ($(UNAME_S),Darwin)
QEMU_DISPLAY := cocoa
else
QEMU_DISPLAY := gtk
endif

QEMU_COMMON := \
    -cdrom $(BUILD)/linux-0.01.iso \
    -drive file=$(BUILD)/root.img,format=raw,if=none,id=hd0 \
    -device ide-hd,drive=hd0,bus=ide.0,unit=0,cyls=977,heads=5,secs=17 \
    -boot d -m 8M -no-reboot

run: all
	$(call STAGE,9/10,launching QEMU (Linus' kernel meets 2026 silicon))
	$(call _curtain_up)
	@$(QEMU) $(QEMU_COMMON) -serial stdio \
	    -d guest_errors,int -D $(BUILD)/qemu.log \
	    -display $(QEMU_DISPLAY)
	@printf '\n$(CGY)  ── curtain down ── log saved to $(BUILD)/qemu.log$(CR)\n'

run-uefi: all
	$(call STAGE,9/10,launching QEMU in UEFI mode)
	@$(QEMU) $(QEMU_COMMON) -serial stdio \
	    -bios $(shell brew --prefix qemu 2>/dev/null)/share/qemu/edk2-i386-code.fd \
	    -display $(QEMU_DISPLAY)

run-headless: all
	$(call STAGE,9/10,running headless (no GUI))
	@$(QEMU) $(QEMU_COMMON) -nographic \
	    -serial file:$(BUILD)/serial.log \
	    -d guest_errors,int -D $(BUILD)/qemu.log
	@printf '  $(CGY)$(G_DOT)$(CR) serial log: $(CWH)$(BUILD)/serial.log$(CR)\n'
	@printf '  $(CGY)$(G_DOT)$(CR) analyze:    $(CWH)make bootmon$(CR)\n'

run-debug: all
	$(call STAGE,9/10,launching QEMU with GDB stub on :1234)
	@printf '  $(CY)gdb attach:$(CR)  target remote :1234\n\n'
	@$(QEMU) $(QEMU_COMMON) -serial stdio -s -S \
	    -d guest_errors,int,cpu_reset -D $(BUILD)/qemu.log \
	    -display $(QEMU_DISPLAY)

run-monitor: all
	$(call STAGE,9/10,launching QEMU with monitor socket)
	@rm -f $(BUILD)/mon.sock
	@$(QEMU) $(QEMU_COMMON) -display none \
	    -monitor unix:$(BUILD)/mon.sock,server,nowait \
	    -serial file:$(BUILD)/serial.log \
	    -daemonize -pidfile $(BUILD)/qemu.pid
	@sleep 2
	@printf '  $(CG)$(G_OK)$(CR) connect: socat - UNIX-CONNECT:$(BUILD)/mon.sock\n'

boom: clean all run

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              CINEMATIC                                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

define _curtain_up
	@bash -c '\
	  chars=("▁" "▂" "▃" "▄" "▅" "▆" "▇" "█"); \
	  msg=("decoding 1991 source……" "warming x86 silicon……" "calling on Linus……" "kernel ready"); \
	  for phase in 0 1 2 3; do \
	    printf "  $(CP)"; \
	    for i in $$(seq 1 56); do printf "%s" "$${chars[$$RANDOM%8]}"; done; \
	    printf "$(CR)  $(CWH)%s$(CR)\n" "$${msg[$$phase]}"; \
	    sleep 0.18; \
	  done; \
	  printf "\n  $(CY)$(G_ARR) handing control to QEMU$(CR)\n\n"'
endef

define _summary
	@printf '\n$(CC1)╔══════════════════════════════════════════════════════════════════════════╗$(CR)\n'
	@printf '$(CC1)║$(CR)  $(CB)$(CG)BUILD COMPLETE$(CR)                                                          $(CC1)║$(CR)\n'
	@printf '$(CC1)╠══════════════════════════════════════════════════════════════════════════╣$(CR)\n'
	@for f in $(BUILD)/kernel.elf $(BUILD)/kernel.bin $(BUILD)/bootstub.elf \
	          $(BUILD)/linux-0.01.iso $(BUILD)/root.img $(BUILD)/shell.bin $(BUILD)/hello.bin; do \
	   if [ -f $$f ]; then \
	     sz=$$(stat -f%z $$f 2>/dev/null || stat -c%s $$f); \
	     printf "$(CC1)║$(CR)  $(CC1)$(G_INF)$(CR) %-32s $(CY)%14s$(CR) bytes  $(CGY)sha1$(CR) $(CP)%s$(CR)  $(CC1)║$(CR)\n" \
	       $$f $$sz $$(shasum $$f | cut -c1-8); \
	   fi; \
	 done
	@printf '$(CC1)╠══════════════════════════════════════════════════════════════════════════╣$(CR)\n'
	@printf '$(CC1)║$(CR)  next:  $(CG)make run$(CR)   |   $(CG)make boom$(CR) (clean+build+run)                       $(CC1)║$(CR)\n'
	@printf '$(CC1)╚══════════════════════════════════════════════════════════════════════════╝$(CR)\n'
endef

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              BOOT MONITOR                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝

bootmon:
	@python3 tools/bootmon.py $(BUILD)/serial.log 2>/dev/null || \
	  python3 tools/bootmon.py

bootmon-live:
	@python3 tools/bootmon.py --live $(BUILD)/serial.log 2>/dev/null || \
	  echo '  $(CRD)no serial.log — run $(CWH)make run-monitor$(CR) first'

bootmon-timeline:
	@python3 tools/bootmon.py --timeline $(BUILD)/serial.log 2>/dev/null || \
	  echo '  $(CRD)no serial.log — run $(CWH)make run$(CR) first'

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              TESTING                                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

test: all
	$(call STAGE,9/10,running QEMU boot test suite)
	@python3 tests/test_boot.py --iso $(BUILD)/linux-0.01.iso \
	  --img $(BUILD)/root.img --timeout 60
	@PYTHONUNBUFFERED=1 python3 tests/test_shell.py --iso $(BUILD)/linux-0.01.iso \
	  --img $(BUILD)/root.img --timeout 120

test-quick:
	$(call STEP,boot test (existing artifacts))
	@python3 tests/test_boot.py --iso $(BUILD)/linux-0.01.iso \
	  --img $(BUILD)/root.img --timeout 15

test-shell: all
	$(call STEP,shell smoke test)
	@PYTHONUNBUFFERED=1 python3 tests/test_shell.py --iso $(BUILD)/linux-0.01.iso \
	  --img $(BUILD)/root.img --timeout 120

test-large-rootfs: all
	$(call STEP,large rootfs shell smoke test)
	@python3 tests/test_large_rootfs.py --iso $(BUILD)/linux-0.01.iso \
	  --mkimage $(BUILD)/mkimage --shell $(BUILD)/shell.bin \
	  --update $(BUILD)/update.bin --hello $(BUILD)/hello.bin \
	  --factor 3 --timeout 120

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              GDB                                         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

gdb:
	@printf '  $(CGY)$(G_DOT)$(CR) attach with: $(CWH)x86_64-elf-gdb $(BUILD)/kernel.elf -x .gdbinit$(CR)\n'
	@printf '  $(CGY)$(G_DOT)$(CR) pretty-printers in $(CWH)gdb/printers.py$(CR)\n'
	@printf '  $(CGY)$(G_DOT)$(CR) commands: $(CWH)task_list$(CR) $(CWH)page_table$(CR) $(CWH)buffer_list$(CR)\n'

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              DIAGNOSTICS                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

doctor:
	$(SPLASH)
	@printf '\n  $(CB)$(CWH)toolchain health check$(CR)\n\n'
	@for tool in $(CC) $(AS) $(LD) $(NM) $(OBJCOPY) $(NASM) $(QEMU) $(XORRISO) socat shasum; do \
	  if command -v $$tool >/dev/null 2>&1; then \
	    v=$$($$tool --version 2>/dev/null | head -1 | cut -c1-50); \
	    printf "  $(CG)$(G_OK)$(CR) %-22s $(CGY)%s$(CR)\n" "$$tool" "$$v"; \
	  else \
	    printf "  $(CRD)$(G_NO)$(CR) %-22s $(CRD)MISSING$(CR)\n" "$$tool"; \
	  fi; \
	done
	@printf '\n  $(CB)$(CWH)limine bootloader$(CR)\n\n'
	@if [ -d $(LIMINE_DIR) ] && [ -f $(LIMINE_BIN) ]; then \
	  printf "  $(CG)$(G_OK)$(CR) %-22s $(CGY)%s$(CR)\n" "limine" "$$($(LIMINE_BIN) version | head -1)"; \
	else \
	  printf "  $(CRD)$(G_NO)$(CR) %-22s $(CRD)not built — $(CR)cd $(LIMINE_DIR) && make\n" "limine"; \
	fi
	@printf '\n  $(CB)$(CWH)platform$(CR)\n\n'
	@printf "  $(CGY)$(G_DOT)$(CR) os               $(CWH)%s$(CR)\n" "$(UNAME_S)"
	@printf "  $(CGY)$(G_DOT)$(CR) qemu display     $(CWH)%s$(CR)\n" "$(QEMU_DISPLAY)"
	@printf "  $(CGY)$(G_DOT)$(CR) build host       $(CWH)%s$(CR)\n" "$(BUILD_HOST)"
	@printf '\n'

info:
	$(SPLASH)
	@printf '\n  $(CB)release$(CR)     $(CY)%s%s$(CR)\n'   "$(RELEASE)" "$(GIT_DIRTY)"
	@printf '  $(CB)git rev$(CR)     $(CP)%s$(CR)\n'      "$(GIT_REV)"
	@printf '  $(CB)built$(CR)       $(CGY)%s on %s$(CR)\n' "$(BUILD_DATE)" "$(BUILD_HOST)"
	@printf '  $(CB)author$(CR)      $(CM)%s$(CR) $(CGY)<%s>$(CR)\n' "$(AUTHOR)" "$(EMAIL)"
	@printf '\n'
	@if [ -d $(BUILD) ]; then \
	  printf '  $(CB)artifacts$(CR)\n'; \
	  for f in $(BUILD)/*.iso $(BUILD)/*.img $(BUILD)/*.bin $(BUILD)/*.elf; do \
	    [ -f $$f ] && printf "    $(CC1)$(G_INF)$(CR) %-32s $(CY)%s$(CR) bytes\n" \
	      "$$f" "$$(stat -f%z $$f 2>/dev/null || stat -c%s $$f)"; \
	  done; \
	fi

sizes: $(BUILD)/kernel.elf
	@printf '\n  $(CB)$(CWH)kernel.elf sections$(CR)\n\n'
	@$(OBJDUMP) -h $< | awk '/^ *[0-9]/ { \
	    "printf '"'"'%d'"'"' 0x"$$3 | getline sz; close("printf '"'"'%d'"'"' 0x"$$3); \
	    printf "  $(CGY)$(G_DOT)$(CR) %-12s $(CY)%6s$(CR) bytes  $(CGY)vma$(CR) $(CP)%s$(CR)\n", $$2, sz, $$4 }'
	@printf '\n  $(CB)$(CWH)visual$(CR)\n\n'
	@$(OBJDUMP) -h $< | awk '/^ *[0-9] *\.(text|rodata|data|bss)/ { \
	    "printf '"'"'%d'"'"' 0x"$$3 | getline sz; close("printf '"'"'%d'"'"' 0x"$$3); \
	    n=int(sz/512)+1; bar=""; \
	    for(i=0;i<n;i++) bar=bar "█"; \
	    printf "  $(CWH)%-8s$(CR) $(CG)%s$(CR) $(CGY)%d$(CR)\n", $$2, bar, sz; \
	  }'
	@printf '\n'

symbols: $(BUILD)/kernel.elf
	@printf '\n  $(CB)$(CWH)top kernel symbols (by address)$(CR)\n\n'
	@$(NM) -n $< | grep ' [TtDdBb] _' | head -30 | \
	  awk '{ printf "  $(CP)%s$(CR) $(CGY)%s$(CR) $(CWH)%s$(CR)\n", $$1, $$2, $$3 }'

hash:
	@printf '\n  $(CB)$(CWH)artifact integrity (sha256)$(CR)\n\n'
	@for f in $(BUILD)/kernel.bin $(BUILD)/kernel.elf $(BUILD)/bootstub.elf \
	          $(BUILD)/linux-0.01.iso $(BUILD)/root.img $(BUILD)/shell.bin $(BUILD)/hello.bin; do \
	  if [ -f $$f ]; then \
	    h=$$(shasum -a 256 $$f | cut -c1-64); \
	    printf "  $(CC1)$(G_INF)$(CR) $(CWH)%-28s$(CR) $(CP)%s$(CR)\n" "$$f" "$$h"; \
	  fi; \
	done

tree:
	@printf '\n  $(CB)$(CWH)source layout$(CR)  $(CGY)(*.c, *.h, *.s, *.S)$(CR)\n\n'
	@find . -type f \( -name '*.c' -o -name '*.h' -o -name '*.s' -o -name '*.S' \) \
	    -not -path './build/*' -not -path './.git/*' | sort | \
	    awk -F/ '{ \
	      depth=NF-2; indent=""; for(i=0;i<depth;i++) indent=indent "  "; \
	      f=$$NF; \
	      printf "  $(CGY)%s│$(CR) $(CWH)%s$(CR)\n", indent, f; \
	    }'

stats:
	@printf '\n  $(CB)$(CWH)1991 → 2026 delta$(CR)\n\n'
	@orig=$$(find ../linux-0.01 -type f \( -name '*.c' -o -name '*.h' -o -name '*.s' \) \
	         -not -path '*/.git/*' 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $$1}'); \
	  mod=$$(find . -type f \( -name '*.c' -o -name '*.h' -o -name '*.s' -o -name '*.S' \) \
	         -not -path './build/*' -not -path './.git/*' | xargs wc -l 2>/dev/null | tail -1 | awk '{print $$1}'); \
	  printf "  $(CGY)$(G_DOT)$(CR) lines of code  upstream Linus 1991:  $(CY)%s$(CR)\n" "$$orig"; \
	  printf "  $(CGY)$(G_DOT)$(CR) lines of code  modern port 2026:     $(CY)%s$(CR)\n" "$$mod"; \
	  if [ -n "$$orig" ] && [ -n "$$mod" ]; then \
	    delta=$$((mod - orig)); \
	    printf "  $(CGY)$(G_DOT)$(CR) delta:                                $(CM)%+d$(CR) lines\n" "$$delta"; \
	  fi
	@printf '\n  $(CB)$(CWH)git activity$(CR)\n\n'
	@git log --pretty=format:'  $(CP)%h$(CR) $(CGY)%ad$(CR) $(CWH)%s$(CR)' --date=short 2>/dev/null | head -8
	@printf '\n\n'

audit:
	@printf '\n  $(CB)$(CWH)diff vs upstream Linus 1991$(CR)\n\n'
	@if [ -d ../linux-0.01 ]; then \
	  diff -rq ../linux-0.01 . 2>/dev/null | grep -v '.git\|build\|userland\|tools' | head -30 | \
	    awk '{ \
	      if ($$1=="Only") { printf "  $(CG)+$(CR) $(CWH)%s$(CR)\n", $$NF } \
	      else { printf "  $(CY)*$(CR) $(CWH)%s$(CR)\n", $$2 } \
	    }'; \
	else \
	  printf "  $(CRD)upstream ../linux-0.01 not found$(CR)\n"; \
	fi
	@printf '\n'

logs:
	@if [ -f $(BUILD)/qemu.log ]; then \
	  printf '\n  $(CB)$(CWH)last 40 lines of qemu.log$(CR)\n\n'; \
	  tail -40 $(BUILD)/qemu.log | sed 's/^/  /'; \
	else \
	  printf '  $(CRD)no qemu.log yet — run `make run` first$(CR)\n'; \
	fi

screenshot:
	@if [ ! -S $(BUILD)/mon.sock ]; then \
	  printf '  $(CRD)QEMU monitor not running — try: $(CWH)make run-monitor$(CR)\n'; exit 1; \
	fi
	@echo "screendump $(PWD)/$(BUILD)/screen.ppm" | socat - UNIX-CONNECT:$(BUILD)/mon.sock >/dev/null
	@sips -s format png $(BUILD)/screen.ppm --out $(BUILD)/screen.png >/dev/null 2>&1 || true
	@printf '  $(CG)$(G_OK)$(CR) screenshot saved: $(CWH)$(BUILD)/screen.png$(CR)\n'

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              CI / WATCH                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

ci: clean all
	@printf '\n  $(CB)$(CWH)CI smoke test$(CR)\n\n'
	@timeout 10 $(QEMU) $(QEMU_COMMON) -display none -nographic \
	    -serial file:$(BUILD)/ci-serial.log \
	    -d guest_errors -D $(BUILD)/ci.log >/dev/null 2>&1 || true
	@if grep -q "Triple Fault\|Reset" $(BUILD)/ci.log; then \
	  printf "  $(CRD)$(G_NO)$(CR) boot failed — see $(BUILD)/ci.log\n"; exit 1; \
	elif grep -q "Ok." $(BUILD)/ci-serial.log 2>/dev/null; then \
	  printf "  $(CG)$(G_OK)$(CR) smoke test passed (root fs mounted)\n"; \
	else \
	  printf "  $(CY)$(G_ARR)$(CR) partial boot — serial: "; \
	  tail -5 $(BUILD)/ci-serial.log 2>/dev/null | tr '\n' ' '; \
	  echo; \
	fi

watch:
	@printf '  $(CB)watching source tree for changes (Ctrl-C to stop)$(CR)\n\n'
	@if command -v fswatch >/dev/null 2>&1; then \
	  fswatch -or boot/ init/ kernel/ mm/ fs/ lib/ include/ userland/ tools/ Makefile | \
	    while read; do clear; $(MAKE) --no-print-directory all; done; \
	elif command -v inotifywait >/dev/null 2>&1; then \
	  while inotifywait -qre modify boot/ init/ kernel/ mm/ fs/ lib/ include/ userland/ tools/ Makefile; do \
	    clear; $(MAKE) --no-print-directory all; \
	  done; \
	else \
	  printf '  $(CRD)install fswatch (macOS) or inotify-tools (linux)$(CR)\n'; \
	fi

backup:
	@tag="release/$(shell echo $(CODENAME) | tr A-Z a-z | tr ' ' '-')-$(VERSION)"; \
	  printf '  $(CB)tagging:$(CR) $(CY)%s$(CR)\n' "$$tag"; \
	  git tag -a "$$tag" -m "$(CODENAME) $(VERSION) — sealed $(BUILD_DATE) by $(AUTHOR)" 2>&1 | sed 's/^/  /' || true; \
	  printf '  $(CG)$(G_OK)$(CR) done. push with: $(CWH)git push origin "$$tag"$(CR)\n'

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              JOURNEY                                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

journey:
	@bash -c '\
	  clear; \
	  $(MAKE) --no-print-directory banner; \
	  sleep 0.6; \
	  declare -a story=( \
	    "$(CGY)1991-09-17, Helsinki, Finland$(CR)" \
	    "$(CWH)Linus posts to comp.os.minix:$(CR)" \
	    "  $(CY)Hello everybody out there using minix —$(CR)" \
	    "  $(CY)Im doing a (free) operating system$(CR)" \
	    "  $(CY)(just a hobby, won t be big and professional like gnu)$(CR)" \
	    "" \
	    "$(CGY)2026-05-23, modern silicon$(CR)" \
	    "  $(CC1)10,243 lines of 1991 source$(CR)" \
	    "  $(CC1)compiled by GCC 13 with $(CB)$(CY)-fleading-underscore$(CR)" \
	    "  $(CC1)loaded by $(CB)$(CM)Limine 8.7$(CR)$(CC1) multiboot2$(CR)" \
	    "  $(CC1)booted on $(CB)$(CG)QEMU i386$(CR)" \
	    "" \
	    "$(CM)the kernel that became the world is breathing again$(CR)" \
	  ); \
	  for line in "$${story[@]}"; do \
	    printf "    %b\n" "$$line"; \
	    sleep 0.35; \
	  done; \
	  echo; \
	  for i in 1 2 3 4 5; do \
	    printf "  $(CP)"; \
	    chars=("▁" "▂" "▃" "▄" "▅" "▆" "▇" "█"); \
	    for j in $$(seq 1 60); do printf "%s" "$${chars[$$RANDOM%8]}"; done; \
	    printf "$(CR)\r"; \
	    sleep 0.12; \
	  done; \
	  echo; echo; \
	  printf "  $(CB)$(CG)$(G_INF8)  ready.  run:  $(CB)$(CWH)make boom$(CR)\n\n"'

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              CLEAN                                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

clean:
	@printf '\n  $(CGY)$(G_DOT)$(CR) clearing object files……\n'
	@rm -f $(ALL_OBJS) boot/bootstub.o $(BUILD)/crt0.o $(BUILD)/hello.o $(BUILD)/shell.o
	@printf '  $(CGY)$(G_DOT)$(CR) clearing build/……\n'
	@rm -rf $(BUILD)
	@printf '  $(CG)$(G_OK)$(CR) workspace pristine\n'

deepclean: clean
	@printf '  $(CGY)$(G_DOT)$(CR) clearing /tmp/limine-src……\n'
	@# Only ever remove a /tmp scratch dir — NEVER a system/brew share path that
	@# LIMINE_DIR may now auto-resolve to. Deleting /usr/local/share/limine here
	@# would nuke the Homebrew install.
	@case "$(LIMINE_DIR)" in /tmp/*) rm -rf "$(LIMINE_DIR)";; *) printf '  $(CGY)$(G_DOT)$(CR) skipping non-/tmp LIMINE_DIR ($(LIMINE_DIR))\n';; esac
	@printf '  $(CG)$(G_OK)$(CR) deep clean done\n'

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              HELP                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

help:
	$(SPLASH)
	@printf '\n  $(CB)$(CWH)usage$(CR)  $(CGY)make <target>$(CR)\n\n'
	@printf '  $(CB)$(CG)build$(CR)\n'
	@printf '    $(CWH)all$(CR)            build kernel + image + ISO (default)\n'
	@printf '    $(CWH)kernel$(CR)         build only the kernel binary\n'
	@printf '    $(CWH)iso$(CR)            build only the ISO\n'
	@printf '    $(CWH)image$(CR)          build only the Minix v1 root image\n'
	@printf '\n  $(CB)$(CC1)launch$(CR)\n'
	@printf '    $(CWH)run$(CR)            $(CY)★$(CR) build + boot in QEMU (the main act)\n'
	@printf '    $(CWH)boom$(CR)           $(CY)★$(CR) clean + build + run (one shot)\n'
	@printf '    $(CWH)run-uefi$(CR)       boot via UEFI firmware\n'
	@printf '    $(CWH)run-debug$(CR)      boot with gdb stub on :1234\n'
	@printf '    $(CWH)run-headless$(CR)   no GUI, all output to stdio\n'
	@printf '    $(CWH)run-monitor$(CR)    daemonize + monitor socket (for $(CWH)screenshot$(CR))\n'
	@printf '\n  $(CB)$(CM)diagnose$(CR)\n'
	@printf '    $(CWH)doctor$(CR)         check toolchain health\n'
	@printf '    $(CWH)info$(CR)           show release / build metadata\n'
	@printf '    $(CWH)sizes$(CR)          kernel section sizes (with bars)\n'
	@printf '    $(CWH)symbols$(CR)        top kernel symbols by address\n'
	@printf '    $(CWH)hash$(CR)           sha256 of all artifacts\n'
	@printf '    $(CWH)logs$(CR)           tail last QEMU run log\n'
	@printf '    $(CWH)screenshot$(CR)     capture current QEMU framebuffer\n'
	@printf '\n  $(CB)$(CY)inspect$(CR)\n'
	@printf '    $(CWH)tree$(CR)           source layout\n'
	@printf '    $(CWH)stats$(CR)          LOC vs upstream Linus 1991\n'
	@printf '    $(CWH)audit$(CR)          diff against upstream\n'
	@printf '\n  $(CB)$(CM)test$(CR)\n'
	@printf '    $(CWH)test$(CR)           build + full boot test in QEMU\n'
	@printf '    $(CWH)test-quick$(CR)     boot test with existing artifacts\n'
	@printf '    $(CWH)test-shell$(CR)     shell smoke test in QEMU\n'
	@printf '    $(CWH)test-large-rootfs$(CR) oversized shell/rootfs smoke test\n'
	@printf '    $(CWH)bootmon$(CR)        decode VGA boot markers from serial.log\n'
	@printf '    $(CWH)bootmon-live$(CR)   live monitor boot progress\n'
	@printf '    $(CWH)bootmon-timeline$(CR) annotated boot timeline\n'
	@printf '\n  $(CB)$(CP)debug$(CR)\n'
	@printf '    $(CWH)run-debug$(CR)      boot with gdb stub on :1234\n'
	@printf '    $(CWH)gdb$(CR)            show GDB pretty-printer info\n'
	@printf '    $(CWH)screenshot$(CR)     capture current QEMU framebuffer\n'
	@printf '\n  $(CB)$(CP)workflow$(CR)\n'
	@printf '    $(CWH)watch$(CR)          auto-rebuild on file change\n'
	@printf '    $(CWH)ci$(CR)             headless smoke test\n'
	@printf '    $(CWH)backup$(CR)         git tag with codename\n'
	@printf '    $(CWH)journey$(CR)        cinematic 1991→2026 story\n'
	@printf '\n  $(CB)$(CRD)clean$(CR)\n'
	@printf '    $(CWH)clean$(CR)          remove build artifacts\n'
	@printf '    $(CWH)deepclean$(CR)      also remove vendored Limine\n'
	@printf '\n'
	@printf '  $(CGY)·······································································$(CR)\n'
	@printf '  $(CGY)"as above, so below — the kernel that booted the world,$(CR)\n'
	@printf '  $(CGY)  boots again in the geometry of vesica piscis."$(CR)   $(CM)$(G_INF8)$(CR)\n\n'

kernel: $(BUILD)/kernel.bin
iso:    $(BUILD)/linux-0.01.iso
image:  $(BUILD)/root.img
