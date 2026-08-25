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
make run EXPERIENCE=alive
build/bemu-linux01 --keys $'/bin/hello\n' --expect 'Hello from C userland'
build/bemu-linux01 --root build/root-1991.img --experience 1991
```

`--experience` accepts `1991` or `alive`; alive is the default. The historical
selector defaults to `build/root-1991.img`, while alive defaults to
`build/root.img`. Both are included in the CRC-checked BBP command line consumed
by the guest. A marker in the otherwise unused MBR boot-code area makes bEMU
reject mismatched profile/image combinations before entering KVM. Unmarked
legacy images are accepted only by alive mode to preserve existing research
images.

The CMOS model takes one coherent UTC snapshot per boot. Historical mode always
starts at `1991-09-17 00:00:00 UTC`, the Linux 0.01 release date; alive mode
starts at the host's current UTC time. Linux reads the same CMOS register model
in both modes and advances time through its PIT-driven `jiffies`; bEMU does not
forge shell command output.

The source retains the upstream BSD-3-Clause license and provenance header.
