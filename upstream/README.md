# Upstream Linux 0.01 Provenance

Source: https://www.kernel.org/pub/linux/kernel/Historic/linux-0.01.tar.gz
Downloaded: 2026-08-22
SHA-256: 24454f830cdb571e2c4ad15481119c43b3cafd48dd869a9b2945d1036d1dc68d

This tarball is the canonical historical source used as the archaeological
reference for the Vesica Piscis artifact. `datasets/patches/` records every
source-path divergence in the declared historical core; `docs/PORTING_LEDGER.md`
groups the available historical interpretations.

## Layout inside the tarball

```
linux/
  Makefile
  boot/
    boot.s
    head.s
  fs/
    buffer.c
    char_dev.c
    ...
  include/
    a.out.h
    ctype.h
    ...
  init/
    main.c
  kernel/
    asm.s
    console.c
    ...
  lib/
    ctype.c
    ...
  mm/
    memory.c
    page.s
  tools/
    build.c
```

## Verification

```bash
(cd upstream && sha256sum -c SHA256SUMS)
```

## License

The historical files remain under the original Linux 0.01 distribution terms.
See `LICENSE` for the complete notice.
