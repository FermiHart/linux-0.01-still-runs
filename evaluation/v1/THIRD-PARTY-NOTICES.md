# Third-Party Notices And Redistribution Provenance

This file is an engineering inventory, not legal advice or a warranty of rights.
The root `LICENSE` and this notice must travel with the package. The Unlicense
text is **not a blanket license** for historical code, third-party material,
linked system libraries, or files carrying their own terms.

## Linux 0.01 Historical Source

The historical core derives from Linux 0.01, Copyright (C) 1991 Linus
Torvalds. Its `RELNOTES-0.01` terms require intact notices and freely available
full source and state that one **may not distribute this for a fee**, including
handling costs. The package supplies the fixed source snapshot, reachable Git
history, and `source/upstream/linux-0.01.tar.gz`, whose expected SHA-256 is:

```text
24454f830cdb571e2c4ad15481119c43b3cafd48dd869a9b2945d1036d1dc68d
```

See `source/LICENSE`, `source/upstream/README.md`, and
`source/upstream/SHA256SUMS`. Evaluator transfer must be without a fee.

## Modern Project Code, BBP, And bEMU

Files with `SPDX-License-Identifier: BSD-3-Clause` are governed by the BSD text
in `source/LICENSE`. Other original modern material is covered only where its
author had the right to apply the stated project terms. Do not infer a directory
license from one SPDX-marked file.

`source/bemu/bemu_linux01.c` declares adaptation from `bEMU-NANO` at the private
path `OS/Nanokernel.org/BasmOS/bemu/bemu_nano.c` and states BSD-3-Clause. The
package preserves that declaration and author identity, but no public upstream
URL, commit, or original-file hash is currently available for independent
verification. Therefore bEMU-NANO provenance is author-declared, not independently
proven by this package.

## GNU C Library Linkage

The packaged `artifacts/bemu-linux01`, `artifacts/mkimage`, and
`artifacts/minix-inspect` use the host GNU C Library through a dynamic PIE
mechanism that permits use of a compatible replacement library. The retained
compiler-case executables also use the host glibc loader/libc as recorded in
`source/datasets/compiler-cases/v1/environment.json`. glibc is licensed under
the GNU Lesser General Public License, version 2.1 or later. The applicable
license text is in `evaluation/licenses/LGPL-2.1.txt`.

The package does not bundle the glibc shared library or Ubuntu's glibc source
packages. Redistributors remain responsible for the notices and source-access
obligations of the exact runtime supplied alongside these executables.

GCC-produced host executables and the 18 retained compiler-case binaries contain
GCC startup/runtime material such as `crtstuff` and may use `libgcc`. GCC runtime
files carrying the GCC Runtime Library Exception may be propagated as eligible
target code under that exception. Its complete text is in
`evaluation/licenses/GCC-RUNTIME-LIBRARY-EXCEPTION-3.1.txt`. This inventory does
not classify GCC code as project-authored material. Ubuntu/GCC/Binutils/NASM
package references otherwise remain build dependencies, not bundled package
archives or an OCI image.

## VGA Font

`source/kernel/vga_font8x8.h` derives from the `vgafont8` table in SeaBIOS.
SeaBIOS attributes the font package to Joseph Gil and states that the individual
fonts are public domain. The pinned reference is:

<https://github.com/coreboot/seabios/blob/81ec9ec0bcf45df11fb7f98339ec9036b546fca0/vgasrc/vgafonts.c>

Do not classify this font as BSD-3-Clause merely because adjacent modern code
uses that license.

## Historical Text And Quotations

`source/userland/shell.c`, `source/README.md`, `source/tools/mkimage.c`, and the
retained console trace contain copies or excerpts of Linus
Torvalds's August 1991 `comp.os.minix` announcement and several attributed
technical quotations. Generated copies also occur in `artifacts/shell.bin` and
the two root images. Attribution is not itself a license. Their inclusion is for
historical commentary in the research experience; broader publication or
commercial redistribution requires a separate rights assessment. The Linux 0.01
source terms and project Unlicense do not silently cover these texts.

## Datasets And Captured Binaries

The patch and trace datasets carry their own manifests and explicit provenance
limits. Compiler-case binaries are retained observations produced with the
recorded GCC/Binutils/glibc environment, not guest components and not complete
archives of every toolchain input. No ephemeral CI log or newly captured trace
is promoted to a dataset by this evaluator package.
