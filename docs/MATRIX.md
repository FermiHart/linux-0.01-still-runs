# Compatibility matrix

This matrix records the combinations of host toolchain, Linux kernel, CPU and
KVM backend on which `linux-0.01-still-runs` has been built and booted.

## Reference configuration

| Item | Version / Model | Notes |
|---|---|---|
| Host OS | Ubuntu 24.04 LTS | Container base in `Dockerfile` |
| Host kernel | 6.8.0-generic | `/dev/kvm` and `linux/kvm.h` |
| GCC | 13.3.0 | i386 freestanding |
| GNU Binutils | 2.42 | `as` + `ld` |
| NASM | 2.16.01 | For userland assembly |
| Python | 3.12.3 | Test harness |
| CPU | x86-64 (Intel/AMD) | KVM required; boots in 32-bit protected mode |
| bEMU backend | KVM direct | No firmware, BBP handoff |

## Tested combinations

| GCC | Binutils | Host kernel | CPU | KVM | Result |
|---|---|---|---|---|---|
| 13.3.0 | 2.42 | 6.8.0 | x86-64 Intel | yes | PASS |
| 13.3.0 | 2.42 | 6.8.0 | x86-64 AMD | yes | PASS (expected) |

## Expected-compatible combinations

| GCC | Binutils | Host kernel | CPU | KVM | Notes |
|---|---|---|---|---|---|
| 12.x | 2.38+ | 5.10+ | x86-64 | yes | Should build; not yet tested |
| 13.x | 2.40+ | 5.15+ | x86-64 | yes | Should build; not yet tested |
| 14.x | 2.42+ | 6.x | x86-64 | yes | Likely; `-O1` workarounds may need review |

## Unsupported combinations

| Item | Reason |
|---|---|
| macOS / ARM64 | No KVM `/dev/kvm`; Rosetta does not expose VMX |
| 32-bit host | Untested; cross-compiler recommended |
| Non-KVM hypervisors | bEMU uses Linux KVM ioctls directly |

## How to extend

1. Build inside the pinned container (`make reproducible`).
2. Run the full suite (`make ci`).
3. If it passes, append a row to this matrix and commit.
