# Bear Boot Protocol (BBP) Specification

This document describes the Bear Boot Protocol (BBP), the tag-based,
UUID-versioned, multi-architecture boot-handoff layer used by
`linux-0.01-still-runs`. BBP is intentionally small: it carries only the
information the kernel needs to take over from a firmware-free runner such as
bEMU.

## Version

- **Major**: 1
- **Minor**: 1 (`v1.1` adds per-reference CRC for out-of-line data, ADR-0006)

## Goals

1. **Stable ABI**: every structure that crosses the boot boundary is sized and
   laid out explicitly. Reordering or resizing a field is a breaking change.
2. **Defensive parsing**: the kernel treats all producer data as untrusted.
   CRC64 detects accidental corruption; it does *not* authenticate a malicious
   producer.
3. **Multi-architecture**: the same ABI supports x86_64, AArch64, RISC-V64,
   LoongArch and x86-32.
4. **Little-endian on the wire**: big-endian targets must byteswap.

## Overview

BBP has two principal structures:

- **`bbp_header`**: emitted by the kernel into the `.bbp_hdr` section. It tells
  the bootloader which tags the kernel wants and how to hand off control.
- **`bbp_info`**: emitted by the bootloader and passed to the kernel in the
  architecture-specific argument register (RDI on x86_64, X0 on AArch64, A0 on
  RISC-V). It carries the actual handoff data as a linked list of tags.

Both structures start with a 16-byte magic, a major/minor version, and a CRC64/XZ
checksum computed with the checksum field set to zero.

## Header (`bbp_header`)

| Offset | Field | Size | Meaning |
|---|---|---|---|
| 0 | `magic` | 16 | `"BEAR_BOOT"` zero-padded |
| 16 | `version_major` | 2 | protocol major version |
| 18 | `version_minor` | 2 | protocol minor version |
| 20 | `header_size` | 4 | `sizeof(struct bbp_header)` |
| 24 | `flags` | 8 | `BBP_HF_*` |
| 32 | `entry_point` | 8 | kernel entry address |
| 40 | `paging_mode` | 8 | `BBP_PAGING_*` |
| 48 | `kernel_virtual_base` | 8 | desired higher-half base |
| 56 | `request_count` | 4 | number of requested tags |
| 60 | `reserved0` | 4 | must be zero |
| 64 | `requests` | 8 | physical pointer to `bbp_tag_request[]` |
| 72 | `kernel_uuid` | 16 | 128-bit kernel UUID |
| 88 | `kernel_name` | 64 | NUL-terminated string |
| 152 | `checksum` | 8 | CRC64/XZ of header |

### Header flags

- `BBP_HF_HIGH_ENTROPY_KASLR`
- `BBP_HF_ENABLE_5LEVEL_PAGING`
- `BBP_HF_UNMAP_NULL_PAGE`
- `BBP_HF_ENABLE_NX`
- `BBP_HF_SMP_BOOT_ALL`
- `BBP_HF_FRAMEBUFFER_WANTED`

## Info (`bbp_info`)

| Offset | Field | Size | Meaning |
|---|---|---|---|
| 0 | `magic` | 16 | `"BEAR_INFO"` zero-padded |
| 16 | `version_major` | 2 | protocol major version |
| 18 | `version_minor` | 2 | protocol minor version |
| 20 | `info_size` | 4 | total bytes including all tags |
| 24 | `bootloader_name` | 32 | producer name |
| 56 | `bootloader_version` | 16 | producer version |
| 72 | `bootloader_uuid` | 16 | 128-bit producer UUID |
| 88 | `bootloader_start_ts` | 8 | nanoseconds |
| 96 | `kernel_load_ts` | 8 | nanoseconds |
| 104 | `handoff_ts` | 8 | nanoseconds |
| 112 | `architecture` | 2 | `BBP_ARCH_*` |
| 114 | `cpu_count` | 2 | number of CPUs |
| 116 | `tag_count` | 4 | number of tags |
| 120 | `first_tag` | 8 | physical pointer to first `bbp_tag_header` |
| 128 | `next_context` | 8 | chain pointer, 0 if none |
| 136 | `checksum` | 8 | CRC64/XZ of info struct |

## Tags

Tags form a singly-linked list. Each tag begins with a common header:

```c
struct bbp_tag_header {
    uint64_t tag_id;     /* BBP_TAG_* */
    uint16_t flags;
    uint16_t reserved0;
    uint32_t body_size;  /* bytes following this header */
    bbp_phys_t next_tag; /* 0 = end of list */
    uint64_t checksum;   /* CRC64/XZ of body, 0 if no body */
} __attribute__((packed));
```

Tag IDs are 64-bit values: bits `[63:48]` are the category and bits `[47:0]`
are the ID within the category.

### Defined tags

- `BBP_TAG_SMP` (core)
- `BBP_TAG_MODULES` (core)
- `BBP_TAG_CMDLINE` (core)
- `BBP_TAG_MEMORY_MAP` (memory)
- `BBP_TAG_HHDM` (memory)
- `BBP_TAG_KERNEL_ADDRESS` (memory)
- `BBP_TAG_FRAMEBUFFER` (device)
- `BBP_TAG_PCIE` (device)
- `BBP_TAG_SECURITY` (security)
- `BBP_TAG_ACPI` (platform)
- `BBP_TAG_DEVICETREE` (platform)
- `BBP_TAG_EFI` (platform)
- `BBP_TAG_HYPERVISOR` (platform)
- `BBP_TAG_SMBIOS` (platform)
- `BBP_TAG_METRICS` (debug)

## Memory map entry

```c
struct bbp_memory_entry {
    uint64_t base;
    uint64_t length;
    uint32_t type;        /* BBP_MEM_* */
    uint32_t attributes;  /* BBP_MEM_ATTR_* */
} __attribute__((packed));
```

Memory types:

- `BBP_MEM_USABLE`
- `BBP_MEM_RESERVED`
- `BBP_MEM_ACPI_RECLAIMABLE`
- `BBP_MEM_ACPI_NVS`
- `BBP_MEM_BAD`

## Checksum rules

- Header checksum covers the entire `bbp_header` with `checksum` set to 0.
- Info checksum covers the entire `bbp_info` with `checksum` set to 0.
- Tag checksum covers only the tag body (not the header) with `checksum` set
  to 0. Out-of-line data referenced by a tag must carry its own per-reference
  CRC (v1.1).

## Producer-consumer contract

1. The kernel emits a `.bbp_hdr` section containing a valid `bbp_header`.
2. The bootloader parses the header, builds the requested tags, and produces a
   `bbp_info`.
3. The kernel validates magic, version, checksum, then walks tags defensively:
   it checks bounds, rejects unknown required tags, and verifies CRCs before
   using data.
4. Pointers in tags are physical addresses; a higher-half kernel must add the
   HHDM offset before dereferencing.

## Authentication limits

CRC64 detects accidental bit flips and some classes of benign corruption. It is
*not* a cryptographic authenticator. A malicious producer can craft a payload
with a valid CRC. BBP assumes the producer is part of the trusted computing
base; the CRC is a data-integrity guard, not a security boundary. See Wave 062
for the full security note.
