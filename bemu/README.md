# bEMU Linux 0.01 Contract

`bemu-linux01` is copied and adapted from `bEMU-NANO` in
`OS/Nanokernel.org/BasmOS/bemu`. It runs this repository's kernel directly
through `/dev/kvm`: no BIOS, firmware, ISO parser or bootloader is involved.

The machine contract loads `build/kernel.bin` at physical address zero,
provides 8 MiB of RAM, and models only the hardware Linux 0.01 uses here:
8259/PIT through KVM, COM1, CMOS, VGA register state, keyboard scancodes and a
CHS IDE disk backed by `build/root.img` or a selected profile image.

The root image is opened read-write and mapped with `MAP_SHARED`; guest writes
therefore target the selected image, subject to the documented IDE completion
limitations. When stdout is a terminal,
bEMU also filters guest OSC/DCS and unsafe control sequences while retaining
the ANSI color, cursor and erase sequences used by the shell. Use
`--raw-console` only when unfiltered terminal output is explicitly required.
Redirected stdout remains byte-for-byte guest serial output.

```sh
make run
make run EXPERIENCE=1991
build/bemu-linux01 --keys $'/bin/hello\n' --expect 'Hello from C userland'
build/bemu-linux01 --root build/root-1991.img --experience 1991
```

`--experience 1991` is validated by the modern CLI, defaults to
`build/root-1991.img`, and is included in the CRC-checked BBP command line
consumed by the guest. A marker in the otherwise unused MBR boot-code area makes
bEMU reject mismatched profile/image combinations before entering KVM.

The source retains the upstream BSD-3-Clause license and provenance header.
