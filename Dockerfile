# linux-0.01-still-runs — Containerized build environment
#
# Build:   docker build -t linux-0.01-still-runs .
# Run:     docker run --rm linux-0.01-still-runs
# Shell:   docker run --rm -it --entrypoint /bin/bash linux-0.01-still-runs
# Export:  docker build --target artifacts --output type=local,dest=. .
#
# Produces: kernel, root image, and the bEMU KVM runner under /build in both
# the default image and the exported artifacts stage.

FROM ubuntu:24.04@sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517 AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    nasm \
    ca-certificates \
    python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY Makefile ./
COPY LICENSE ./
COPY bbp/ bbp/
COPY bemu/ bemu/
COPY boot/ boot/
COPY fs/ fs/
COPY include/ include/
COPY init/ init/
COPY kernel/ kernel/
COPY lib/ lib/
COPY mm/ mm/
COPY tools/mkimage.c tools/mkimage.c
COPY userland/ userland/

RUN make all
RUN install -d -m 0755 /build \
    && install -m 0644 build/root.img build/kernel.elf build/kernel.bin /build/ \
    && install -m 0644 LICENSE /build/LICENSE \
    && install -m 0755 build/bemu-linux01 /build/bemu-linux01

FROM scratch AS artifacts
COPY --from=builder /build/ /build/

FROM builder
CMD ["make", "all"]
