# syntax=docker/dockerfile:1
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

# Reproducible build environment for linux-0.01-still-runs.
# This container provides the reference toolchain documented in docs/TOOLCHAIN.md.
#
# Build:
#   docker build -t linux001-still-runs:latest .
#
# Run (KVM access requires --device /dev/kvm):
#   docker run --rm -it --device /dev/kvm \
#     -v "$(pwd):/work" -w /work \
#     linux001-still-runs:latest make ci

FROM ubuntu:24.04@sha256:e0a1f2ca717d2dd2d5a5bee1110f32a7f14378c49e675f302b10fddc2eba7aa6

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.10ubuntu1 \
    gcc-13=13.3.0-6ubuntu2~24.04.1 \
    g++-13=13.3.0-6ubuntu2~24.04.1 \
    binutils=2.42-4ubuntu2.5 \
    nasm=2.16.01-1build1 \
    python3=3.12.3-0ubuntu2 \
    python3-venv=3.12.3-0ubuntu2 \
    make=4.3-4.1build2 \
    git=1:2.43.0-1ubuntu1.2 \
    ca-certificates=20240203 \
    libc6-dev=2.39-0ubuntu8.5 \
    linux-headers-generic=6.8.0-51.52 \
    util-linux=2.39.3-9ubuntu6.5 \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 100 \
    --slave /usr/bin/g++ g++ /usr/bin/g++-13

WORKDIR /work
