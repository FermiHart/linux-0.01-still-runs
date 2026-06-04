; ============================================================
; sh.asm  -  FERMIHART mini-ash for linux-0.01 (userland)
; F E R M I ~ H A R T  <contact@fermihart.com>
;   ("~" stands in for the canonical infinity glyph; console.c
;    only renders ASCII 32..126 so the literal glyph would be
;    filtered out.)
;
; Assemble flat:  nasm -f bin sh.asm -o sh.bin
; Runs at user CS:0, syscalls via int $0x80 (eax = nr).
; ============================================================

BITS 32
org 0

%define __NR_exit   1
%define __NR_read   3
%define __NR_write  4
%define __NR_time   13
%define __NR_uname  59

_entry:
    ; ---- banner ----------------------------------------------
    mov     eax, __NR_write
    mov     ebx, 1
    mov     ecx, banner
    mov     edx, banner_len
    int     0x80

.loop:
    ; ---- prompt ----------------------------------------------
    mov     eax, __NR_write
    mov     ebx, 1
    mov     ecx, prompt
    mov     edx, prompt_len
    int     0x80

    ; ---- read line ------------------------------------------
    mov     eax, __NR_read
    mov     ebx, 0
    mov     ecx, buf
    mov     edx, 79
    int     0x80
    test    eax, eax
    jle     .quit
    mov     edi, buf
    add     edi, eax
    dec     edi
    cmp     byte [edi], 10
    jne     .check
    mov     byte [edi], 0

.check:
    movzx   eax, byte [buf]
    cmp     al, 0
    je      .loop                  ; empty
    cmp     al, 'h'
    je      .help
    cmp     al, 'u'
    je      .uname
    cmp     al, 'd'
    je      .date
    cmp     al, 'c'
    je      .clear
    cmp     al, 'p'
    je      .panic
    cmp     al, 'e'
    je      .quit

    ; ---- unknown --------------------------------------------
    mov     eax, __NR_write
    mov     ebx, 1
    mov     ecx, unk_msg
    mov     edx, unk_len
    int     0x80
    jmp     .loop

.help:
    mov     eax, __NR_write
    mov     ebx, 1
    mov     ecx, help_msg
    mov     edx, help_len
    int     0x80
    jmp     .loop

.clear:
    mov     eax, __NR_write
    mov     ebx, 1
    mov     ecx, clear_str
    mov     edx, clear_len
    int     0x80
    jmp     .loop

.uname:
    sub     esp, 64
    mov     eax, __NR_uname
    mov     ebx, esp
    int     0x80
    mov     eax, __NR_write
    mov     ebx, 1
    mov     ecx, uname_hdr
    mov     edx, uname_hdr_len
    int     0x80
    mov     eax, __NR_write
    mov     ebx, 1
    mov     ecx, esp
    mov     edx, 9              ; utsname.sysname[9]
    int     0x80
    mov     eax, __NR_write
    mov     ebx, 1
    mov     ecx, nl
    mov     edx, 1
    int     0x80
    add     esp, 64
    jmp     .loop

.date:
    mov     eax, __NR_time
    xor     ebx, ebx
    int     0x80
    ; convert eax (unix time) to decimal in num_buf
    mov     edi, num_buf + 15
    mov     byte [edi], 10
    dec     edi
    mov     ecx, 10
.d_div:
    xor     edx, edx
    div     ecx
    add     dl, '0'
    mov     [edi], dl
    dec     edi
    test    eax, eax
    jnz     .d_div
    inc     edi                  ; first digit
    mov     eax, __NR_write
    mov     ebx, 1
    mov     ecx, date_hdr
    mov     edx, date_hdr_len
    int     0x80
    mov     eax, __NR_write
    mov     ebx, 1
    mov     ecx, edi
    lea     edx, [num_buf + 16]
    sub     edx, edi
    int     0x80
    jmp     .loop

.panic:
    ; trigger divide-by-zero  ->  kernel die("divide error")
    xor     eax, eax
    div     eax
    ; unreachable

.quit:
    mov     eax, __NR_write
    mov     ebx, 1
    mov     ecx, bye_msg
    mov     edx, bye_len
    int     0x80
    mov     eax, __NR_exit
    xor     ebx, ebx
    int     0x80
    ; if exit fails, spin
.halt:
    jmp     .halt

; ============================================================
;                            DATA
; ============================================================

%define ESC 27

banner:
    db  ESC,"[2J",ESC,"[H"                       ; clear + home
    db  ESC,"[1;36m"                              ; bold cyan
    db  "  +==========================================+",10
    db  "  |  F E R M I    H A R T   mini-ash         |",10
    db  "  |  running on linux-0.01 (Torvalds, 1991)  |",10
    db  "  +==========================================+",10
    db  ESC,"[0m"
    db  ESC,"[33m"
    db  "  commands: help  uname  date  clear  panic  exit",10
    db  ESC,"[0m",10
banner_len equ $-banner

prompt:
    db  ESC,"[1;32m","fermi",ESC,"[0;37m",":"
    db  ESC,"[1;34m","/",ESC,"[0m","$ "
prompt_len equ $-prompt

help_msg:
    db  ESC,"[36m"
    db  "  help   - show this list",10
    db  "  uname  - kernel system name",10
    db  "  date   - seconds since epoch",10
    db  "  clear  - clear the screen",10
    db  "  panic  - trigger a /0 trap (kernel die)",10
    db  "  exit   - leave the shell",10
    db  ESC,"[0m"
help_len equ $-help_msg

clear_str:
    db  ESC,"[2J",ESC,"[H"
clear_len equ $-clear_str

uname_hdr:
    db  ESC,"[35msysname=",ESC,"[0m"
uname_hdr_len equ $-uname_hdr

date_hdr:
    db  ESC,"[35mepoch=",ESC,"[0m"
date_hdr_len equ $-date_hdr

unk_msg:
    db  ESC,"[31m","? unknown command - try 'help'",ESC,"[0m",10
unk_len equ $-unk_msg

bye_msg:
    db  10,ESC,"[35m","  -=-  farewell  -=-",ESC,"[0m",10
bye_len equ $-bye_msg

nl:        db 10
buf:       times 80 db 0
num_buf:   times 16 db 0
