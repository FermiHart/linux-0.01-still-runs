# linux-0.01-still-runs — Containerized build environment
#
# Build:   docker build -t linux-0.01-still-runs .
# Run:     docker run --rm -it linux-0.01-still-runs
# Shell:   docker run --rm -it --entrypoint /bin/bash linux-0.01-still-runs
#
# Produces: /build/linux-0.01.iso  and  /build/root.img

FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    nasm \
    qemu-system-x86 \
    xorriso \
    git \
    ca-certificates \
    x86_64-elf-gcc \
    x86_64-elf-binutils \
    python3 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth=1 -b v8.x https://github.com/limine-bootloader/limine.git /tmp/limine-src \
    && make -C /tmp/limine-src

WORKDIR /src
COPY . .

RUN mkdir -p /build
RUN make all 2>&1

FROM scratch AS artifacts
COPY --from=builder /src/build/linux-0.01.iso /build/linux-0.01.iso
COPY --from=builder /src/build/root.img /build/root.img
COPY --from=builder /src/build/kernel.elf /build/kernel.elf
COPY --from=builder /src/build/kernel.bin /build/kernel.bin
COPY --from=builder /src/build/bootstub.elf /build/bootstub.elf

FROM builder
CMD ["make", "run"]
