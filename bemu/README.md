# bEMU Linux 0.01 Contract

`bemu-linux01` is copied and adapted from `bEMU-NANO` in
`OS/Nanokernel.org/BasmOS/bemu`. It runs this repository's kernel directly
through `/dev/kvm`: no BIOS, firmware, ISO parser or bootloader is involved.

The machine contract validates `build/kernel.bin` and loads its payload at
physical address zero,
provides 8 MiB of RAM, and models only the hardware Linux 0.01 uses here:
8259/PIT through KVM, COM1, CMOS, VGA register state, keyboard scancodes and a
CHS IDE disk backed by `build/root.img` or a selected profile image.

Before `/dev/kvm` is opened, the modern bridge allocates exactly 8 MiB, requires
the versioned `L01KIMG1` trailer, rejects an empty payload or one larger than
512 KiB, proves every destination range fits
without integer wrap or overlap with the bootstrap GDT and BBP window, loads the
kernel, and builds the reserved BBP handoff. Allocation and short-read failures
are injectable through internal host-side APIs for deterministic unit tests; no
RAM-size or fault switch is exposed by the historical CLI. Runtime load failures
exit with status 1 and a stable `[bemu-linux01]` diagnostic.

The guest-side production consumer treats that handoff as untrusted. It bounds
all pointers to `0xC0000..0xD0000`, validates header and tag CRC64 values before
using bodies, limits and terminates the linked tag walk, rejects duplicate or
missing required tags, then verifies bEMU's exact architecture, identity, HHDM,
memory map, kernel address, hypervisor evidence, and experience command line.
`make test-bbp-corruption` proves these failures in a disposable host mapping by
linking the exact `bbp_linux01_init()` and `bbp_init_win()` production sources;
it does not enter KVM or mutate boot artifacts.

The 16-byte kernel trailer contains `L01KIMG1` and the little-endian payload
length. It remains host-side and is never copied into guest RAM or reported in
the BBP kernel size. Missing, truncated, or length-mismatched trailers are
rejected. Legacy raw kernels are intentionally not accepted because their
actual length cannot be distinguished from suffix truncation. Released
consumers that require a flat payload must validate and remove the final 16
bytes; `build/kernel.raw` is only an internal build intermediate.

The root image is opened read-write and mapped with `MAP_SHARED`; guest writes
therefore target the selected image, subject to the documented IDE completion
limitations. The host-side IDE test API can arm one read or write failure at a
selected LBA. A matching command reports ATA abort/`ERR`, raises IRQ14 before
transferring that sector, and consumes the fault once. This proof seam is not a
guest capability or CLI option. When stdout is a terminal,
bEMU also filters guest OSC/DCS and unsafe control sequences while retaining
the ANSI color, cursor and erase sequences used by the shell. Use
`--raw-console` only when unfiltered terminal output is explicitly required.
Redirected stdout remains byte-for-byte guest serial output.

Writes use a 512-byte staging buffer and reach the `MAP_SHARED` virtual medium
only as complete sectors. A host-only, one-shot power-cut seam selects an LBA
and one semantic boundary: write accepted, payload received, sector committed,
or normal unmasked completion IRQ requested. A cut discards staged bytes, lowers
IRQ14, clears transfer state, and ignores later command/data/control PIO until
reset. `make test-power-cut` runs
that state machine under ASan/UBSan and on disposable copies of both root
profiles, requiring exact 0/512/1024-byte deltas and repeatable hashes. `msync`
only makes the already-committed test state inspectable; this is not a model or
claim of physical-media, controller-cache, guest-handler, or filesystem recovery
behavior. No power-cut control is exposed to the guest or CLI.

The common host IRQ bridge also supports one test-only lost or duplicated edge
for IRQ0-15. A dropped assertion suppresses its matching deassertion. A duplicate
passes the original edge, then waits for a completed KVM run, a low device line,
and quiescent IRR/ISR state before replaying one pulse. For slave IRQs, both the
selected slave bit and the master cascade must be clear. This proves host line
policy, not that Linux handles every duplicate or recovers from unsafe IRQ1/IRQ14
faults. No IRQ fault switch is exposed to the guest or CLI.

The host keyboard boundary has a test-only seam for the unambiguous Set-1 error
bytes `0x00` and `0xff`. It validates that each injected byte reaches the
controller latch and requests IRQ1 exactly once before normal input resumes.
Terminal escape decoding persists across short reads and 128-byte poll
boundaries. At non-terminal EOF, a lone `ESC` becomes an Escape keystroke while
an incomplete CSI or SS3 sequence is discarded with a stable diagnostic. This
host-side evidence does not claim guest handler entry or recovery from arbitrary
malformed multi-byte scancode streams, and no keyboard fault switch is exposed.

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
