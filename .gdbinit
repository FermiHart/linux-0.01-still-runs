# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

# linux-0.01-modern GDB init
# Usage: x86_64-elf-gdb build/kernel.elf -x .gdbinit

set arch i386
set tdesc filename /dev/null
set confirm off

source gdb/printers.py

define hook-stop
    printf "  ◄ stopped at 0x%08x\n", $eip
    if $eip >= 0x4000
        # We're past boot, likely in kernel C code
        # Try to show current task
    end
end
