# ════════════════════════════════════════════════════════════════════════════
#
#   linux-0.01-still-runs  —  Makefile  [ Vesica Piscis Edition ]
#
#   Author    : F E R M I ∞ H A R T  <contact@fermihart.com>
#   Subject   : Linus Torvalds' first kernel (1991) booting on 2026 iron
#   Codename  : Vesica Piscis      Channel: v0.1 FOREVER
#   License   : Linux 0.01 terms / BSD-3-Clause / Unlicense (see LICENSE)
#
#   First time?  →  make help
#   Show off?    →  make boom        (clean + build + launch bEMU)
#   Daily work?  →  make run         (build incrementally + run)
#
# ════════════════════════════════════════════════════════════════════════════

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
.DELETE_ON_ERROR:

# ──────────────────────────────────────────────── identity ──────────────────
CODENAME   := Vesica Piscis
VERSION    := 0.01
RELEASE    := $(CODENAME)-$(VERSION)
AUTHOR     := F E R M I ∞ H A R T
EMAIL      := contact@fermihart.com
BUILD_DATE := $(shell \
  epoch="$${SOURCE_DATE_EPOCH:-}"; \
  if [ -n "$$epoch" ]; then \
    date -u -d "@$$epoch" +%Y-%m-%dT%H:%M:%SZ; \
  else \
    date -u +%Y-%m-%dT%H:%M:%SZ; \
  fi)
BUILD_HOST := $(shell hostname -s 2>/dev/null || hostname)
GIT_REV    := $(shell git rev-parse --short HEAD 2>/dev/null || echo "no-git")
GIT_DIRTY  := $(shell test -z "$$(git status --porcelain 2>/dev/null)" && printf ' ' || printf '★')
UNAME_S    := $(shell uname -s)
REPO_ROOT  := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))
BUILD      ?= build
MAKE_COMMAND := $(MAKE)
export BUILD MAKE_COMMAND

ARTIFACT_NAMES := kernel.elf kernel.bin root.img bemu-linux01 mkimage \
                  shell.bin update.bin hello.bin
ARTIFACTS = $(addprefix $(BUILD)/,$(ARTIFACT_NAMES))

# ──────────────────────────────────────────────── toolchain ─────────────────
# Prefer a cross-compiler when one is installed. Linux can use its native
# freestanding toolchain because every target is explicitly built as i386.
# Override with `make PREFIX=/path/to/bin/x86_64-elf-` when needed.
PREFIX ?= $(shell \
  if [ -f "$(BUILD)/.cross_prefix" ]; then \
    read -r p < "$(BUILD)/.cross_prefix"; \
    if [ -x "$$p/bin/x86_64-elf-gcc" ]; then \
      printf '%s/bin/x86_64-elf-' "$$p"; exit 0; \
    fi; \
  fi; \
  if command -v x86_64-elf-gcc >/dev/null 2>&1; then printf 'x86_64-elf-'; \
  elif [ -x "$(HOME)/.local/cross/bin/x86_64-elf-gcc" ]; then printf '%s/.local/cross/bin/x86_64-elf-' "$(HOME)"; \
  elif [ -x /opt/cross/bin/x86_64-elf-gcc ]; then printf '/opt/cross/bin/x86_64-elf-'; \
  elif [ "$(UNAME_S)" = Linux ]; then printf ''; \
  else printf 'x86_64-elf-'; fi)
CC         := $(PREFIX)gcc
AS         := $(PREFIX)as
LD         := $(PREFIX)ld
OBJCOPY    := $(PREFIX)objcopy
OBJDUMP    := $(PREFIX)objdump
NM         := $(PREFIX)nm
NASM       := nasm
HOSTCC     ?= cc

# ──────────────────────────────────────────────── flags ─────────────────────
COMMON_FLAGS = -m32 -march=i386 \
               -ffreestanding -nostdinc -fno-pie -fno-pic \
               -fno-stack-protector -fno-asynchronous-unwind-tables \
               -fno-builtin -fno-strict-aliasing -fleading-underscore -fno-omit-frame-pointer \
               -mpreferred-stack-boundary=2 \
               -Wall -Werror -O2

CFLAGS  := $(COMMON_FLAGS) -std=gnu89 -Iinclude
ASFLAGS := --32
LDFLAGS := -m elf_i386 -nostdlib -z noexecstack -z max-page-size=0x1000 --no-warn-rwx-segments
DEPFLAGS = -MMD -MP -MF $(@:.o=.d) -MT $@

HOSTCFLAGS ?= -O2 -Wall -Wextra -Wformat=2 -Wformat-security \
              -Werror=format-security -fstack-protector-strong \
              -D_FORTIFY_SOURCE=2 -fPIE
HOSTLDFLAGS ?= -pie -Wl,-z,relro,-z,now -Wl,-z,noexecstack
BEMU_LDFLAGS ?= -static-pie -Wl,-z,relro,-z,now -Wl,-z,noexecstack

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
    lib/write.o lib/dup.o lib/setsid.o lib/execve.o lib/wait.o lib/string.o \
    lib/sync.o

INIT_OBJS := init/main.o
HEAD_OBJ  := boot/head.o

# ── Bear Boot Protocol (BBP) — native linux-0.01 port ────────────────────────
# Additive, non-fatal CRC-checksummed boot-handoff layer. Lives in bbp/.
# The BBP core REQUIRES C99+ (for-initializer declarations), but the 1991
# kernel builds -std=gnu89; so the BBP objects get their OWN -std=gnu11 while
# keeping every OTHER kernel flag — crucially -fleading-underscore, so the glue
# resolves _printk / _panic exactly like the rest of the kernel. See bbp/.
BBP_OBJS := bbp/bbp_kernel.o bbp/linux01_bbp.o

ALL_OBJS := $(HEAD_OBJ) $(INIT_OBJS) $(KERNEL_OBJS) $(MM_OBJS) $(FS_OBJS) $(LIB_OBJS) $(BBP_OBJS)
SOURCE_DEPFILES := $(filter-out boot/head.d,$(ALL_OBJS:.o=.d))
DEPFILES := $(SOURCE_DEPFILES) $(BUILD)/hello.d $(BUILD)/shell.d $(BUILD)/mkimage.d

-include $(DEPFILES)

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
.PHONY: help all clean run run-headless kernel image bemu dirs boom doctor info \
        sizes symbols hash checksums tree stats audit provenance journey watch ci backup \
        reproducible verify-reproducible release-check artifact inspect-rootfs \
        fsck-rootfs banner require-artifacts test test-quick test-shell test-large-rootfs \
        test-fs-write test-fs-mkdir test-fs-link test-fs-large test-fs-property \
        test-fs-inspect test-fs-real toolchain

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              MAIN BUILD                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

all: banner
	@$(MAKE) --no-print-directory $(BUILD)/kernel.bin $(BUILD)/root.img $(BUILD)/bemu-linux01
	@$(call _summary)

banner:
	$(SPLASH)

dirs:
	@repo_root="$(REPO_ROOT)"; \
	  build_abs="$$(python3 -c 'import os; print(os.path.realpath(os.environ["BUILD"]))')"; \
	  case "$$build_abs" in \
	    "$$repo_root/build"|"$$repo_root/build"/*) ;; \
	    *) printf '  $(CRD)$(G_NO)$(CR) refusing BUILD outside the canonical repository build tree: %s\n' "$$build_abs" >&2; exit 1 ;; \
	  esac; \
	  mkdir -p -- "$$build_abs"

%.o: %.c
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s\n' "$<" "$@"
	@$(CC) $(CFLAGS) $(DEPFLAGS) -c -o "$@" "$<"

# fs/buffer.c + fs/bitmap.c: -O2 mis-compiles the buffer-cache walk and
# new_block's getblk result handling on modern GCC (Heisenbug — masked by
# any printk in the hot path, repros only with debug-free -O2). Drop to
# -O1 here only. Same class as the sys_ioctl `volatile int ret` fix.
fs/buffer.o: fs/buffer.c
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s $(CGY)[-O1 heisenbug]$(CR)\n' "$<" "$@"
	@$(CC) $(filter-out -O2,$(CFLAGS)) -O1 $(DEPFLAGS) -c -o "$@" "$<"

fs/bitmap.o: fs/bitmap.c
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s $(CGY)[-O1 heisenbug]$(CR)\n' "$<" "$@"
	@$(CC) $(filter-out -O2,$(CFLAGS)) -O1 $(DEPFLAGS) -c -o "$@" "$<"

# kernel/vsprintf.c: -O2 miscompiles the `%s` case (va_arg(char*) fetch) on
# modern GCC — a non-empty %s renders garbage (the pointer is read off by a
# slot), while %x/%c/%d are fine. Same heisenbug class as fs/buffer.o and
# fs/bitmap.o above. The 1991 boot path only ever passed empty strings to %s
# (hd.c "Partition table%s"), so this latent bug went unseen until the BBP
# adapter printed a real status string. Drop to -O1 here only.
kernel/vsprintf.o: kernel/vsprintf.c
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s $(CGY)[-O1 %%s heisenbug]$(CR)\n' "$<" "$@"
	@$(CC) $(filter-out -O2,$(CFLAGS)) -O1 $(DEPFLAGS) -c -o "$@" "$<"

# ── BBP objects: same kernel flags (incl. -fleading-underscore so _printk /
# _panic resolve), but -std=gnu11 (the core uses C99 for-initializer
# declarations) plus the BBP core + compat-shim include paths.
BBP_CFLAGS := $(filter-out -std=gnu89,$(COMMON_FLAGS)) -std=gnu11 \
              -Ibbp/include -Ibbp/compat -Iinclude

# Each BBP object is pinned explicitly: GNU make 3.81 (macOS bundled) does not
# reliably prefer the shorter-stem `bbp/%.o` over the generic `%.o: %.c`, so a
# pattern rule alone could be shadowed and silently compile with the wrong
# (gnu89, no-BBP-include) flags. Explicit targets guarantee BBP_CFLAGS.
#
# Keep explicit BBP prerequisites for first-build clarity; generated -MMD
# dependency files maintain the complete transitive set after compilation.
BBP_HDRS := bbp/include/bbp/bbp.h bbp/include/bbp/bbp_crc64.h \
            bbp/bbp_kernel.h bbp/linux01_bbp.h bbp/linux01_handoff.h \
            bbp/compat/stdint.h bbp/compat/stddef.h

bbp/bbp_kernel.o:  bbp/bbp_kernel.c $(BBP_HDRS)
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s $(CGY)[bbp gnu11]$(CR)\n' "$<" "$@"
	@$(CC) $(BBP_CFLAGS) $(DEPFLAGS) -c -o "$@" "$<"
bbp/linux01_bbp.o: bbp/linux01_bbp.c $(BBP_HDRS)
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s $(CGY)[bbp gnu11]$(CR)\n' "$<" "$@"
	@$(CC) $(BBP_CFLAGS) $(DEPFLAGS) -c -o "$@" "$<"

# init/main.c includes bbp/linux01_bbp.h (the call site), which pulls <bbp/bbp.h>.
# It still compiles -std=gnu89 like the rest of the kernel (the BBP headers are
# gnu89-clean), it just needs the BBP header search paths. Additive override.
init/main.o: init/main.c bbp/linux01_bbp.h bbp/bbp_kernel.h bbp/include/bbp/bbp.h
	@printf '  $(CGY)cc  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s\n' "$<" "$@"
	@$(CC) $(CFLAGS) -Ibbp -Ibbp/include -Ibbp/compat $(DEPFLAGS) -c -o "$@" "$<"

%.o: %.s
	@printf '  $(CGY)as  $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s\n' "$<" "$@"
	@$(AS) $(ASFLAGS) -o "$@" "$<"

%.o: %.S
	@printf '  $(CGY)cpp $(CR) $(CWH)%-40s$(CR) $(CGY)→$(CR) %s\n' "$<" "$@"
	@$(CC) $(CFLAGS) $(DEPFLAGS) -c -o "$@" "$<"

$(BUILD)/kernel.elf: $(ALL_OBJS) boot/kernel.ld | dirs
	$(call STAGE,5/10,linking kernel.elf @ phys 0x00000000)
	@$(LD) $(LDFLAGS) -T boot/kernel.ld -o "$@" $(ALL_OBJS) 2>&1 | sed 's/^/    /'
	$(call OK,kernel.elf ready)

$(BUILD)/kernel.bin: $(BUILD)/kernel.elf
	@$(OBJCOPY) -O binary "$<" "$@"
	@printf '  $(CC1)$(G_INF)$(CR) %-22s $(CY)%s$(CR) bytes\n' \
	  "kernel.bin" "$$(stat -f%z $@ 2>/dev/null || stat -c%s $@)"

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              USERLAND                                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

$(BUILD)/sh.bin: userland/sh.asm | dirs
	$(call STEP,assembling userland/sh.asm (mini-ash))
	@$(NASM) -f bin "$<" -o "$@"

$(BUILD)/update.bin: userland/update.asm | dirs
	$(call STEP,assembling userland/update.asm (sync daemon))
	@$(NASM) -f bin "$<" -o "$@"

# ── Userland C programs ───────────────────────────────────────────

$(BUILD)/crt0.o: userland/crt0.S | dirs
	$(call STEP,assembling userland/crt0.S (C runtime))
	@$(AS) $(ASFLAGS) -o "$@" "$<"

$(BUILD)/hello.bin: userland/programs/hello.c $(BUILD)/crt0.o | dirs
	$(call STEP,compiling userland/programs/hello.c (C userland demo))
	@$(CC) $(CFLAGS) -Iuserland -MMD -MP -MF "$(BUILD)/hello.d" -MT "$@" \
	  -c userland/programs/hello.c -o "$(BUILD)/hello.o"
	@$(LD) $(LDFLAGS) -Ttext 0 -e _entry "$(BUILD)/crt0.o" "$(BUILD)/hello.o" -o "$(BUILD)/hello.elf"
	@$(OBJCOPY) -O binary "$(BUILD)/hello.elf" "$(BUILD)/hello.bin"
	@printf '  $(CC1)$(G_INF)$(CR) %-22s $(CY)%s$(CR) bytes\n' \
	  "hello.bin" "$$(stat -f%z $(BUILD)/hello.bin 2>/dev/null || stat -c%s $(BUILD)/hello.bin)"

$(BUILD)/shell.bin: userland/shell.c $(BUILD)/crt0.o | dirs
	$(call STEP,compiling userland/shell.c (interactive shell))
	@$(CC) $(filter-out -O2,$(CFLAGS)) -Os -Iuserland \
	  -MMD -MP -MF "$(BUILD)/shell.d" -MT "$@" \
	  -c userland/shell.c -o "$(BUILD)/shell.o"
	@$(LD) $(LDFLAGS) -Ttext 0 -e _entry "$(BUILD)/crt0.o" "$(BUILD)/shell.o" -o "$(BUILD)/shell.elf"
	@$(OBJCOPY) -O binary "$(BUILD)/shell.elf" "$(BUILD)/shell.bin"
	@printf '  $(CC1)$(G_INF)$(CR) %-22s $(CY)%s$(CR) bytes\n' \
	  "shell.bin" "$$(stat -f%z $(BUILD)/shell.bin 2>/dev/null || stat -c%s $(BUILD)/shell.bin)"

# ── Host tools ────────────────────────────────────────────────────

$(BUILD)/mkimage: tools/mkimage.c | dirs
	$(call STEP,building tools/mkimage (Minix v1 + MBR forge))
	@$(HOSTCC) $(HOSTCFLAGS) -MMD -MP -MF "$(BUILD)/mkimage.d" -MT "$@" \
	  -o "$@" "$<" $(HOSTLDFLAGS)

$(BUILD)/minix-inspect: tools/minix-inspect.c | dirs
	$(call STEP,building tools/minix-inspect)
	@$(HOSTCC) $(HOSTCFLAGS) -MMD -MP -MF "$(BUILD)/minix-inspect.d" -MT "$@" \
	  -o "$@" "$<" $(HOSTLDFLAGS)

# Collect all userland binaries (ASM + C)
USERLAND_BINS := $(BUILD)/shell.bin $(BUILD)/update.bin $(BUILD)/hello.bin

$(BUILD)/root.img: $(BUILD)/mkimage $(USERLAND_BINS)
	$(call STAGE,7/10,forging Minix v1 root filesystem)
	@"$(BUILD)/mkimage" "$@" "$(BUILD)/shell.bin" "$(BUILD)/update.bin" "$(BUILD)/hello.bin" 2>&1 | sed 's/^/    /'
	$(call OK,root.img forged)

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                                bEMU                                      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

$(BUILD)/bemu-linux01: bemu/bemu_linux01.c bbp/bbp_build.c bbp/bbp_build.h \
                        bbp/linux01_handoff.h bbp/include/bbp/bbp.h \
                        bbp/include/bbp/bbp_crc64.h | dirs
	$(call STAGE,8/10,building firmware-free bEMU KVM runner)
	@$(HOSTCC) $(HOSTCFLAGS) -Werror -std=gnu11 -Ibbp/include \
	  -o "$@" bemu/bemu_linux01.c bbp/bbp_build.c $(BEMU_LDFLAGS)
	$(call OK,bemu-linux01 ready)

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              RUN TARGETS                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

run: all
	$(call STAGE,9/10,launching bEMU (direct KVM, no firmware))
	$(call _curtain_up)
	@"$(BUILD)/bemu-linux01" --kernel "$(BUILD)/kernel.bin" --root "$(BUILD)/root.img"

run-headless: run

boom:
	@$(MAKE) --no-print-directory clean
	@$(MAKE) --no-print-directory run

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
	  printf "\n  $(CY)$(G_ARR) handing control to bEMU/KVM$(CR)\n\n"'
endef

define _summary
	@printf '\n$(CC1)╔══════════════════════════════════════════════════════════════════════════╗$(CR)\n'
	@printf '$(CC1)║$(CR)  $(CB)$(CG)BUILD COMPLETE$(CR)                                                          $(CC1)║$(CR)\n'
	@printf '$(CC1)╠══════════════════════════════════════════════════════════════════════════╣$(CR)\n'
	@for f in $(ARTIFACTS); do \
	   if [ -f $$f ]; then \
	     sz=$$(stat -f%z $$f 2>/dev/null || stat -c%s $$f); \
	     h=$$(if command -v sha256sum >/dev/null 2>&1; then sha256sum "$$f"; else shasum -a 256 "$$f"; fi | cut -c1-8); \
	     printf "$(CC1)║$(CR)  $(CC1)$(G_INF)$(CR) %-32s $(CY)%14s$(CR) bytes  $(CGY)sha256$(CR) $(CP)%s$(CR)  $(CC1)║$(CR)\n" \
	       $$f $$sz $$h; \
	   fi; \
	 done
	@printf '$(CC1)╠══════════════════════════════════════════════════════════════════════════╣$(CR)\n'
	@printf '$(CC1)║$(CR)  next:  $(CG)make run$(CR)   |   $(CG)make boom$(CR) (clean+build+run)                       $(CC1)║$(CR)\n'
	@printf '$(CC1)╚══════════════════════════════════════════════════════════════════════════╝$(CR)\n'
endef

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              TESTING                                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

test: all
	$(call STAGE,9/10,running bEMU boot test suite)
	@python3 tests/test_harness_utils.py
	@python3 tests/test_boot.py --bemu $(BUILD)/bemu-linux01 \
	  --kernel $(BUILD)/kernel.bin --img $(BUILD)/root.img --timeout 30
	@PYTHONUNBUFFERED=1 python3 tests/test_shell.py --bemu $(BUILD)/bemu-linux01 \
	  --kernel $(BUILD)/kernel.bin --img $(BUILD)/root.img --timeout 120
	@PYTHONUNBUFFERED=1 python3 tests/test_shell.py --bemu $(BUILD)/bemu-linux01 \
	  --kernel $(BUILD)/kernel.bin --img $(BUILD)/root.img --timeout 120 --interactive
	@python3 tests/test_large_rootfs.py --bemu $(BUILD)/bemu-linux01 \
	  --kernel $(BUILD)/kernel.bin --mkimage $(BUILD)/mkimage \
	  --shell $(BUILD)/shell.bin --update $(BUILD)/update.bin \
	  --hello $(BUILD)/hello.bin --factor 3 --timeout 120

require-artifacts:
	@missing=0; \
	  for f in "$(BUILD)/bemu-linux01" "$(BUILD)/kernel.bin" "$(BUILD)/root.img"; do \
	    if [ ! -f "$$f" ]; then \
	      printf '  $(CRD)$(G_NO)$(CR) missing required artifact: %s\n' "$$f" >&2; \
	      missing=1; \
	    fi; \
	  done; \
	  if [ "$$missing" -ne 0 ]; then \
	    printf '  $(CY)$(G_ARR)$(CR) run $(CWH)make all$(CR) first\n' >&2; \
	    exit 1; \
	  fi

test-quick: require-artifacts
	$(call STEP,boot test (existing artifacts))
	@python3 tests/test_boot.py --bemu $(BUILD)/bemu-linux01 \
	  --kernel $(BUILD)/kernel.bin --img $(BUILD)/root.img --timeout 30

test-shell: all
	$(call STEP,shell smoke test)
	@PYTHONUNBUFFERED=1 python3 tests/test_shell.py --bemu $(BUILD)/bemu-linux01 \
	  --kernel $(BUILD)/kernel.bin --img $(BUILD)/root.img --timeout 120

test-large-rootfs: all
	$(call STEP,large rootfs shell smoke test)
	@python3 tests/test_large_rootfs.py --bemu $(BUILD)/bemu-linux01 --kernel $(BUILD)/kernel.bin \
	  --mkimage $(BUILD)/mkimage --shell $(BUILD)/shell.bin \
	  --update $(BUILD)/update.bin --hello $(BUILD)/hello.bin \
	  --factor 3 --timeout 120

test-fs-write: all
	$(call STEP,fs write/append/truncate test)
	@PYTHONUNBUFFERED=1 python3 tests/test_fs_write.py --bemu $(BUILD)/bemu-linux01 \
	  --kernel $(BUILD)/kernel.bin --img $(BUILD)/root.img --timeout 120

test-fs-mkdir: all
	$(call STEP,fs mkdir/rmdir test)
	@PYTHONUNBUFFERED=1 python3 tests/test_fs_mkdir.py --bemu $(BUILD)/bemu-linux01 \
	  --kernel $(BUILD)/kernel.bin --img $(BUILD)/root.img --timeout 120

test-fs-link: all
	$(call STEP,fs link/unlink/rename test)
	@PYTHONUNBUFFERED=1 python3 tests/test_fs_link.py --bemu $(BUILD)/bemu-linux01 \
	  --kernel $(BUILD)/kernel.bin --img $(BUILD)/root.img --timeout 120

test-fs-large: all
	$(call STEP,fs multi-line file test)
	@PYTHONUNBUFFERED=1 python3 tests/test_fs_large.py --bemu $(BUILD)/bemu-linux01 \
	  --kernel $(BUILD)/kernel.bin --img $(BUILD)/root.img --timeout 120

test-fs-property: all
	$(call STEP,fs property-style test)
	@PYTHONUNBUFFERED=1 python3 tests/test_fs_property.py --bemu $(BUILD)/bemu-linux01 \
	  --kernel $(BUILD)/kernel.bin --img $(BUILD)/root.img --timeout 120

test-fs-inspect: $(BUILD)/root.img $(BUILD)/minix-inspect
	$(call STEP,independent fs inspector consistency test)
	@python3 tests/test_fs_inspect.py --minix-inspect $(BUILD)/minix-inspect \
	  --img $(BUILD)/root.img

test-fs-real: all
	$(call STEP,real filesystem verification)
	@PYTHONUNBUFFERED=1 python3 tests/test_fs_real.py --bemu $(BUILD)/bemu-linux01 \
	  --kernel $(BUILD)/kernel.bin --img $(BUILD)/root.img --timeout 120

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              DIAGNOSTICS                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

doctor:
	$(SPLASH)
	@printf '\n  $(CB)$(CWH)toolchain health check$(CR)\n\n'
	@status=0; \
	  for tool in $(CC) $(AS) $(LD) $(NM) $(OBJCOPY) $(OBJDUMP) $(NASM) \
	              $(HOSTCC) python3 make awk sed find sort git mktemp stat cut \
	              diff tr xargs wc seq clear; do \
	    if command -v "$$tool" >/dev/null 2>&1; then \
	      printf "  $(CG)$(G_OK)$(CR) %-22s $(CGY)%s$(CR)\n" "$$tool" "$$(command -v "$$tool")"; \
	    else \
	      printf "  $(CRD)$(G_NO)$(CR) %-22s $(CRD)MISSING$(CR)\n" "$$tool"; \
	      status=1; \
	    fi; \
	  done; \
	  if command -v sha256sum >/dev/null 2>&1 || command -v shasum >/dev/null 2>&1; then \
	    printf "  $(CG)$(G_OK)$(CR) %-22s $(CGY)available$(CR)\n" "SHA-256 tool"; \
	  else \
	    printf "  $(CRD)$(G_NO)$(CR) %-22s $(CRD)MISSING$(CR)\n" "SHA-256 tool"; \
	    status=1; \
	  fi; \
	  tmp=$$(mktemp -d "$${TMPDIR:-/tmp}/linux001-doctor.XXXXXXXX"); \
	  trap 'rm -rf -- "$$tmp"' EXIT; \
	  if printf 'void f(void) {}\n' | $(CC) $(COMMON_FLAGS) -x c -c -o "$$tmp/kernel.o" - >/dev/null 2>&1; then \
	    printf "  $(CG)$(G_OK)$(CR) %-22s $(CGY)i386 freestanding$(CR)\n" "compiler probe"; \
	  else \
	    printf "  $(CRD)$(G_NO)$(CR) %-22s $(CRD)i386 flags rejected$(CR)\n" "compiler probe"; \
	    status=1; \
	  fi; \
	  if printf 'int main(void) { return 0; }\n' | $(HOSTCC) $(HOSTCFLAGS) -x c -o "$$tmp/host" - $(BEMU_LDFLAGS) >/dev/null 2>&1; then \
	    printf "  $(CG)$(G_OK)$(CR) %-22s $(CGY)static PIE$(CR)\n" "host linker probe"; \
	  else \
	    printf "  $(CRD)$(G_NO)$(CR) %-22s $(CRD)static PIE unavailable$(CR)\n" "host linker probe"; \
	    status=1; \
	  fi; \
	  printf '\n  $(CB)$(CWH)virtualization$(CR)\n\n'; \
	  if [ "$(UNAME_S)" = Linux ] && [ -r /usr/include/linux/kvm.h ] && \
	     [ -r /dev/kvm ] && [ -w /dev/kvm ]; then \
	    printf "  $(CG)$(G_OK)$(CR) %-22s $(CGY)headers + read/write$(CR)\n" "/dev/kvm"; \
	  else \
	    printf "  $(CRD)$(G_NO)$(CR) %-22s $(CRD)KVM unavailable$(CR)\n" "/dev/kvm"; \
	    status=1; \
	  fi; \
	  printf '\n  $(CB)$(CWH)platform$(CR)\n\n'; \
	  printf "  $(CGY)$(G_DOT)$(CR) os               $(CWH)%s$(CR)\n" "$(UNAME_S)"; \
	  printf "  $(CGY)$(G_DOT)$(CR) boot backend     $(CWH)bEMU/KVM$(CR)\n"; \
	  printf "  $(CGY)$(G_DOT)$(CR) build host       $(CWH)%s$(CR)\n\n" "$(BUILD_HOST)"; \
	  exit "$$status"

info:
	$(SPLASH)
	@printf '\n  $(CB)release$(CR)     $(CY)%s%s$(CR)\n'   "$(RELEASE)" "$(GIT_DIRTY)"
	@printf '  $(CB)git rev$(CR)     $(CP)%s$(CR)\n'      "$(GIT_REV)"
	@printf '  $(CB)built$(CR)       $(CGY)%s on %s$(CR)\n' "$(BUILD_DATE)" "$(BUILD_HOST)"
	@printf '  $(CB)author$(CR)      $(CM)%s$(CR) $(CGY)<%s>$(CR)\n' "$(AUTHOR)" "$(EMAIL)"
	@printf '\n'
	@if [ -d $(BUILD) ]; then \
	  printf '  $(CB)artifacts$(CR)\n'; \
	  for f in $(BUILD)/*.img $(BUILD)/*.bin $(BUILD)/*.elf $(BUILD)/bemu-linux01; do \
	    [ -f $$f ] && printf "    $(CC1)$(G_INF)$(CR) %-32s $(CY)%s$(CR) bytes\n" \
	      "$$f" "$$(stat -f%z $$f 2>/dev/null || stat -c%s $$f)"; \
	  done; \
	fi

sizes: $(BUILD)/kernel.elf
	@printf '\n  $(CB)$(CWH)kernel.elf sections$(CR)\n\n'
	@$(OBJDUMP) -h "$<" | while read -r index name hex_size vma rest; do \
	  case "$$index" in *[!0-9]*|'') continue ;; esac; \
	  size=$$((16#$$hex_size)); \
	  printf '  $(CGY)$(G_DOT)$(CR) %-12s $(CY)%6d$(CR) bytes  $(CGY)vma$(CR) $(CP)%s$(CR)\n' \
	    "$$name" "$$size" "$$vma"; \
	done
	@printf '\n  $(CB)$(CWH)visual$(CR)\n\n'
	@$(OBJDUMP) -h "$<" | while read -r index name hex_size rest; do \
	  case "$$name" in .text|.rodata|.data|.bss) ;; *) continue ;; esac; \
	  size=$$((16#$$hex_size)); n=$$(((size + 511) / 512)); \
	  [ "$$n" -gt 0 ] || n=1; \
	  printf -v bar '%*s' "$$n" ''; bar=$${bar// /█}; \
	  printf '  $(CWH)%-8s$(CR) $(CG)%s$(CR) $(CGY)%d$(CR)\n' "$$name" "$$bar" "$$size"; \
	done
	@printf '\n'

symbols: $(BUILD)/kernel.elf
	@printf '\n  $(CB)$(CWH)top kernel symbols (by address)$(CR)\n\n'
	@$(NM) -n $< | awk '$$2 ~ /^[TtDdBb]$$/ && $$3 ~ /^_/ && shown < 30 { \
	  printf "  $(CP)%s$(CR) $(CGY)%s$(CR) $(CWH)%s$(CR)\n", $$1, $$2, $$3; shown++ }'

hash: $(ARTIFACTS)
	@printf '\n  $(CB)$(CWH)artifact integrity (sha256)$(CR)\n\n'
	@for f in $(ARTIFACTS); do \
	  h=$$(if command -v sha256sum >/dev/null 2>&1; then sha256sum "$$f"; else shasum -a 256 "$$f"; fi | cut -c1-64); \
	  printf "  $(CC1)$(G_INF)$(CR) $(CWH)%-28s$(CR) $(CP)%s$(CR)\n" "$$f" "$$h"; \
	done

checksums: $(ARTIFACTS)
	@tmp="$(BUILD)/.SHA256SUMS.tmp"; \
	  trap 'rm -f -- "$$tmp"' EXIT; \
	  : > "$$tmp"; \
	  for f in $(ARTIFACTS); do \
	    h=$$(if command -v sha256sum >/dev/null 2>&1; then sha256sum "$$f"; else shasum -a 256 "$$f"; fi | cut -c1-64); \
	    printf '%s  %s\n' "$$h" "$${f#$(BUILD)/}" >> "$$tmp"; \
	  done; \
	  if command -v sha256sum >/dev/null 2>&1; then \
	    (cd "$(BUILD)" && sha256sum --check .SHA256SUMS.tmp >/dev/null); \
	  else \
	    (cd "$(BUILD)" && shasum -a 256 --check .SHA256SUMS.tmp >/dev/null); \
	  fi; \
	  mv -- "$$tmp" "$(BUILD)/SHA256SUMS"; \
	  trap - EXIT; \
	  printf '  $(CG)$(G_OK)$(CR) wrote and verified $(CWH)%s$(CR)\n' "$(BUILD)/SHA256SUMS"

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
	@orig=""; \
	  if [ -d ../linux-0.01 ]; then \
	    orig=$$(find ../linux-0.01 -type f \( -name '*.c' -o -name '*.h' -o -name '*.s' \) \
	           -not -path '*/.git/*' -print0 | xargs -0r wc -l | tail -1 | awk '{print $$1}'); \
	  fi; \
	  mod=$$(find . -type f \( -name '*.c' -o -name '*.h' -o -name '*.s' -o -name '*.S' \) \
	         -not -path './build/*' -not -path './.git/*' -print0 | xargs -0r wc -l | tail -1 | awk '{print $$1}'); \
	  if [ -n "$$orig" ]; then \
	    printf "  $(CGY)$(G_DOT)$(CR) lines of code  upstream Linus 1991:  $(CY)%s$(CR)\n" "$$orig"; \
	  else \
	    printf "  $(CGY)$(G_DOT)$(CR) lines of code  upstream Linus 1991:  $(CY)%s$(CR)\n" \
	      "not available (expected at ../linux-0.01)"; \
	  fi; \
	  printf "  $(CGY)$(G_DOT)$(CR) lines of code  modern port 2026:     $(CY)%s$(CR)\n" "$$mod"; \
	  if [ -n "$$orig" ] && [ -n "$$mod" ]; then \
	    delta=$$((mod - orig)); \
	    printf "  $(CGY)$(G_DOT)$(CR) delta:                                $(CM)%+d$(CR) lines\n" "$$delta"; \
	  fi
	@printf '\n  $(CB)$(CWH)git activity$(CR)\n\n'
	@git log --max-count=8 --pretty=format:'  $(CP)%h$(CR) $(CGY)%ad$(CR) $(CWH)%s$(CR)' --date=short 2>/dev/null
	@printf '\n\n'

audit:
	@bash "$(REPO_ROOT)/scripts/audit.sh" | tail -n 1 | xargs -I{} printf '\n  $(CG)$(G_OK)$(CR) wrote $(CWH){}$(CR)\n'

provenance:
	@bash "$(REPO_ROOT)/scripts/provenance.sh" | tail -n 1 | xargs -I{} printf '\n  $(CG)$(G_OK)$(CR) wrote $(CWH){}$(CR)\n'

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              CI / WATCH                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

ci:
	@$(MAKE) --no-print-directory clean
	@$(MAKE) --no-print-directory test
	@$(MAKE) --no-print-directory checksums

reproducible:
	@export SOURCE_DATE_EPOCH="$${SOURCE_DATE_EPOCH-1700000000}"; \
	  printf '\n  $(CB)$(CWH)reproducible build$(CR)  $(CGY)SOURCE_DATE_EPOCH=$(CP)%s$(CR)\n\n' "$$SOURCE_DATE_EPOCH"; \
	  $(MAKE) --no-print-directory clean; \
	  $(MAKE) --no-print-directory all; \
	  $(MAKE) --no-print-directory checksums; \
	  if [ ! -f "$(BUILD)/SHA256SUMS" ]; then \
	    printf '  $(CRD)$(G_NO)$(CR) $(BUILD)/SHA256SUMS missing\n' >&2; \
	    exit 1; \
	  fi; \
	  cp "$(BUILD)/SHA256SUMS" "$(BUILD)/REPRODUCIBLE.sha256"; \
	  printf '\n  $(CG)$(G_OK)$(CR) wrote $(CWH)$(BUILD)/REPRODUCIBLE.sha256$(CR)\n'

verify-reproducible:
	@bash "$(REPO_ROOT)/scripts/verify-reproducibility.sh"

release-check:
	@bash "$(REPO_ROOT)/scripts/release-check.sh"

artifact:
	@bash "$(REPO_ROOT)/scripts/make-artifact.sh"

inspect-rootfs: $(BUILD)/root.img $(BUILD)/minix-inspect
	@"$(BUILD)/minix-inspect" "$(BUILD)/root.img"

fsck-rootfs: $(BUILD)/root.img
	@bash "$(REPO_ROOT)/scripts/fsck-rootfs.sh"

watch:
	@printf '  $(CB)watching source tree for changes (Ctrl-C to stop)$(CR)\n\n'
	@rebuild() { \
	    clear 2>/dev/null || true; \
	    if ! "$${MAKE_COMMAND}" -j1 --no-print-directory all; then \
	      printf '  $(CRD)$(G_NO)$(CR) build failed; waiting for the next source change\n' >&2; \
	    fi; \
	  }; \
	  if command -v fswatch >/dev/null 2>&1; then \
	  fswatch -r bbp/ bemu/ boot/ init/ kernel/ mm/ fs/ lib/ include/ userland/ tools/ Makefile | \
	    while IFS= read -r changed; do \
	      case "$$changed" in *.c|*.h|*.s|*.S|*.asm|*.ld|*/Makefile|Makefile) \
	        rebuild ;; esac; \
	    done; \
	elif command -v inotifywait >/dev/null 2>&1; then \
	  inotifywait -qmr -e close_write,create,delete,move --format '%w%f' \
	    bbp/ bemu/ boot/ init/ kernel/ mm/ fs/ lib/ include/ userland/ tools/ Makefile | \
	    while IFS= read -r changed; do \
	      case "$$changed" in *.c|*.h|*.s|*.S|*.asm|*.ld|*/Makefile|Makefile) \
	        rebuild ;; esac; \
	    done; \
	else \
	  printf '  $(CY)$(G_ARR)$(CR) fswatch/inotifywait unavailable; using 1s polling\n'; \
	  snapshot() { \
	    { find bbp bemu boot init kernel mm fs lib include userland tools -type f \
	        \( -name '*.c' -o -name '*.h' -o -name '*.s' -o -name '*.S' \
	           -o -name '*.asm' -o -name '*.ld' -o -name Makefile \) \
	        -printf '%T@ %s %p\n'; \
	      stat -c '%Y %s Makefile' Makefile; } | \
	      if command -v sha256sum >/dev/null 2>&1; then sha256sum | cut -c1-64; \
	      else shasum -a 256 | cut -c1-64; fi; \
	  }; \
	  before=$$(snapshot); \
	  while sleep 1; do \
	    after=$$(snapshot); \
	    if [ "$$after" != "$$before" ]; then \
	      before="$$after"; rebuild; before=$$(snapshot); \
	    fi; \
	  done; \
	fi

backup:
	@tag="release/$(shell echo $(CODENAME) | tr A-Z a-z | tr ' ' '-')-$(VERSION)"; \
	  if ! worktree=$$(git status --porcelain --untracked-files=all); then \
	    printf '  $(CRD)$(G_NO)$(CR) could not inspect the git worktree\n' >&2; exit 1; \
	  fi; \
	  if [ -n "$$worktree" ]; then \
	    printf '  $(CRD)$(G_NO)$(CR) refusing to tag a dirty worktree\n' >&2; exit 1; \
	  fi; \
	  if git rev-parse -q --verify "refs/tags/$$tag" >/dev/null; then \
	    printf '  $(CRD)$(G_NO)$(CR) tag already exists: %s\n' "$$tag" >&2; exit 1; \
	  fi; \
	  printf '  $(CB)tagging:$(CR) $(CY)%s$(CR)\n' "$$tag"; \
	  git tag -a "$$tag" -m "$(CODENAME) $(VERSION) — sealed $(BUILD_DATE) by $(AUTHOR)" 2>&1 | sed 's/^/  /'; \
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
	    "  $(CC1)loaded directly by $(CB)$(CM)bEMU-NANO$(CR)$(CC1) through BBP$(CR)" \
	    "  $(CC1)booted on $(CB)$(CG)KVM i386$(CR)" \
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
	@repo_root="$(REPO_ROOT)"; \
	  build_abs="$$(python3 -c 'import os; print(os.path.realpath(os.environ["BUILD"]))')"; \
	  case "$$build_abs" in \
	    "$$repo_root/build"|"$$repo_root/build"/*) ;; \
	    *) printf '  $(CRD)$(G_NO)$(CR) refusing to remove BUILD outside the canonical repository build tree: %s\n' "$$build_abs" >&2; exit 1 ;; \
	  esac; \
	  printf '\n  $(CGY)$(G_DOT)$(CR) clearing object files……\n'; \
	  rm -f -- $(ALL_OBJS) $(SOURCE_DEPFILES) bbp/*.o; \
	  printf '  $(CGY)$(G_DOT)$(CR) clearing %s……\n' "$$build_abs"; \
	  rm -rf -- "$$build_abs"
	@printf '  $(CG)$(G_OK)$(CR) workspace pristine\n'

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              HELP                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

help:
	$(SPLASH)
	@printf '\n  $(CB)$(CWH)usage$(CR)  $(CGY)make <target>$(CR)\n\n'
	@printf '  $(CB)$(CG)build$(CR)\n'
	@printf '    $(CWH)all$(CR)            build kernel + image + bEMU\n'
	@printf '    $(CWH)kernel$(CR)         build only the kernel binary\n'
	@printf '    $(CWH)image$(CR)          build only the Minix v1 root image\n'
	@printf '    $(CWH)bemu$(CR)           build only the KVM runner\n'
	@printf '\n  $(CB)$(CC1)launch$(CR)\n'
	@printf '    $(CWH)run$(CR)            $(CY)★$(CR) build + boot directly with bEMU\n'
	@printf '    $(CWH)boom$(CR)           $(CY)★$(CR) clean + build + run (one shot)\n'
	@printf '    $(CWH)run-headless$(CR)   alias for the terminal-native bEMU run\n'
	@printf '\n  $(CB)$(CM)diagnose$(CR)\n'
	@printf '    $(CWH)doctor$(CR)         check toolchain health\n'
	@printf '    $(CWH)info$(CR)           show release / build metadata\n'
	@printf '    $(CWH)sizes$(CR)          kernel section sizes (with bars)\n'
	@printf '    $(CWH)symbols$(CR)        top kernel symbols by address\n'
	@printf '    $(CWH)hash$(CR)           sha256 of all artifacts\n'
	@printf '    $(CWH)checksums$(CR)      write + verify build/SHA256SUMS\n'
	@printf '\n  $(CB)$(CY)inspect$(CR)\n'
	@printf '    $(CWH)tree$(CR)           source layout\n'
	@printf '    $(CWH)stats$(CR)          LOC vs upstream Linus 1991\n'
	@printf '    $(CWH)audit$(CR)          line diff vs upstream (build/AUDIT.txt)\n'
	@printf '    $(CWH)provenance$(CR)     write build/PROVENANCE.txt\n'
	@printf '\n  $(CB)$(CM)test$(CR)\n'
	@printf '    $(CWH)test$(CR)           build + full boot test in bEMU\n'
	@printf '    $(CWH)test-quick$(CR)     boot test with existing artifacts\n'
	@printf '    $(CWH)test-shell$(CR)     shell smoke test in bEMU\n'
	@printf '    $(CWH)test-large-rootfs$(CR) oversized shell/rootfs smoke test\n'
	@printf '    $(CWH)test-fs-write$(CR)   write/append/truncate smoke test\n'
	@printf '    $(CWH)test-fs-mkdir$(CR)  mkdir/rmdir smoke test\n'
	@printf '    $(CWH)test-fs-link$(CR)   link/unlink/rename smoke test\n'
	@printf '    $(CWH)test-fs-large$(CR)  multi-line file smoke test\n'
	@printf '    $(CWH)test-fs-property$(CR) property-style fs test\n'
	@printf '    $(CWH)test-fs-inspect$(CR) independent fs inspector check\n'
	@printf '    $(CWH)test-fs-real$(CR)   real filesystem verification\n'
	@printf '\n  $(CB)$(CP)inspect filesystem$(CR)\n'
	@printf '    $(CWH)inspect-rootfs$(CR)  dump Minix v1 structure of build/root.img\n'
	@printf '    $(CWH)fsck-rootfs$(CR)    validate root.img with fsck.minix\n'
	@printf '\n  $(CB)$(CP)workflow$(CR)\n'
	@printf '    $(CWH)watch$(CR)          auto-rebuild on file change\n'
	@printf '    $(CWH)ci$(CR)             clean build + full tests + checksums\n'
	@printf '    $(CWH)reproducible$(CR)   clean build with SOURCE_DATE_EPOCH\n'
	@printf '    $(CWH)verify-reproducible$(CR) double-build byte compare\n'
	@printf '    $(CWH)release-check$(CR)  independent release verification\n'
	@printf '    $(CWH)artifact$(CR)       create release tarball\n'
	@printf '    $(CWH)toolchain$(CR)      auto-install all tools (detects OS)\n'
	@printf '    $(CWH)backup$(CR)         git tag with codename\n'
	@printf '    $(CWH)journey$(CR)        cinematic 1991→2026 story\n'
	@printf '\n  $(CB)$(CRD)clean$(CR)\n'
	@printf '    $(CWH)clean$(CR)          remove build artifacts\n'
	@printf '\n'
	@printf '  $(CGY)·······································································$(CR)\n'
	@printf '  $(CGY)"as above, so below — the kernel that booted the world,$(CR)\n'
	@printf '  $(CGY)  boots again in the geometry of vesica piscis."$(CR)   $(CM)$(G_INF8)$(CR)\n\n'

kernel: $(BUILD)/kernel.bin
image:  $(BUILD)/root.img
bemu:   $(BUILD)/bemu-linux01
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                            TOOLCHAIN SETUP                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

toolchain:
	@printf '\n  $(CB)$(CWH)setting up toolchain$(CR)\n\n'
	@bash tools/setup-toolchain.sh
