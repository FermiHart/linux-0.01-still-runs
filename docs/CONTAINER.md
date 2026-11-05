# Container pinning

This document describes the reproducible container environment used to build
and test `linux-0.01-still-runs`.

## Base image

| Image | Digest |
|---|---|
| `ubuntu:24.04` | `sha256:e0a1f2ca717d2dd2d5a5bee1110f32a7f14378c49e675f302b10fddc2eba7aa6` |

The digest pins the exact Ubuntu 24.04 layer used for the reference build.

## Pinned packages

The Dockerfile installs the following package versions, matching the reference
toolchain in `docs/TOOLCHAIN.md`:

| Package | Version |
|---|---|
| `build-essential` | `12.10ubuntu1` |
| `gcc-13` | `13.3.0-6ubuntu2~24.04.1` |
| `g++-13` | `13.3.0-6ubuntu2~24.04.1` |
| `binutils` | `2.42-4ubuntu2.5` |
| `nasm` | `2.16.01-1build1` |
| `python3` | `3.12.3-0ubuntu2` |
| `python3-venv` | `3.12.3-0ubuntu2` |
| `make` | `4.3-4.1build2` |
| `git` | `1:2.43.0-1ubuntu1.2` |
| `ca-certificates` | `20240203` |
| `libc6-dev` | `2.39-0ubuntu8.5` |
| `linux-headers-generic` | `6.8.0-51.52` |

## Usage

Build the image:

```bash
docker build -t linux001-still-runs:latest .
```

Run the full CI suite inside the container, passing through `/dev/kvm`:

```bash
docker run --rm -it --device /dev/kvm \
  -v "$(pwd):/work" -w /work \
  linux001-still-runs:latest make ci
```

If `/dev/kvm` is not available, the build itself will succeed but the bEMU test
suite will fail because this project boots the kernel through hardware-assisted
KVM virtualization.

## Verification

The image should be rebuilt whenever `Dockerfile` or the pinned package versions
change. A CI run inside the container is the acceptance test for the lock file.
