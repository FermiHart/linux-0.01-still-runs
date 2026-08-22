# bEMU Linux 0.01 Contract

`bemu-linux01` is copied and adapted from `bEMU-NANO` in
`OS/Nanokernel.org/BasmOS/bemu`. It runs this repository's kernel directly
through `/dev/kvm`: no BIOS, firmware, ISO parser or bootloader is involved.

The machine contract loads `build/kernel.bin` at physical address zero,
provides 8 MiB of RAM, and models only the hardware Linux 0.01 uses here:
8259/PIT through KVM, COM1, CMOS, VGA register state, keyboard scancodes and a
CHS IDE disk backed privately by `build/root.img`.

The root image is opened read-only; guest writes go to a private writable
mapping and are discarded when the runner exits. When stdout is a terminal,
bEMU also filters guest OSC/DCS and unsafe control sequences while retaining
the ANSI color, cursor and erase sequences used by the shell. Use
`--raw-console` only when unfiltered terminal output is explicitly required.
Redirected stdout remains byte-for-byte guest serial output.

```sh
make run
build/bemu-linux01 --keys $'/bin/hello\n' --expect 'Hello from C userland'
```

The source retains the upstream BSD-3-Clause license and provenance header.
