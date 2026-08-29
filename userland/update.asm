; Author: F E R M I INFINITY H A R T <contact@fermihart.com>
; SPDX-License-Identifier: Unlicense

; ============================================================
; update.asm  -  /bin/update stub (block-cache sync daemon)
; F E R M I ~ H A R T  <contact@fermihart.com>
;
; Linus' init() forks /bin/update so it can periodically sync
; dirty buffers. We stub it: pause() forever. The kernel still
; calls sys_sync() on shell exit, so data isn't lost.
; ============================================================

BITS 32
org 0

%define __NR_pause 29

_entry:
    mov     eax, __NR_pause
    int     0x80
    jmp     _entry
