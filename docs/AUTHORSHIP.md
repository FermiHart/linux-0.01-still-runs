# Authorship And File Provenance

## Canonical Identity

The public project identity is:

```text
F E R M I ∞ H A R T <contact@fermihart.com>
```

New ASCII-only source headers spell the symbol as `INFINITY`; established
modern headers that already use `∞` retain that spelling. `AUTHORS.md` records
the creator, principal author, research lead, and current maintainer roles.

## Attribution Rules

Files are not attributed by directory inference. The repository deliberately
mixes historical, modern, adapted, generated, and third-party material, even
inside directories such as `kernel/`, `include/`, `lib/`, and `bemu/`.

| Category | Attribution rule | License/provenance rule |
|---|---|---|
| Original modern source | `Author: F E R M I INFINITY H A R T <contact@fermihart.com>` | Exact per-file license in the manifest; current files use `Unlicense`, except the 11 named BBP files marked `BSD-3-Clause` |
| Modern source with embedded historical text | Canonical author for the original implementation | Explicit mixed-content pointer instead of a blanket per-file Unlicense claim |
| Mixed public document | Canonical author for original prose only | Quotations retain their separate rights boundary |
| Aggregated legal notice | Multiple named licensors/authors | A collection of terms, never one blanket license |
| bEMU source | `Maintainer and adaptation` by the canonical author | The runner preserves its existing BSD declaration; split modules carry no inferred SPDX license while bEMU-NANO provenance remains partial |
| Linux 0.01 source | Linus Torvalds, 1991 | Original Linux 0.01 terms in `LICENSE`; no project `Author:` header is inserted |
| Identity-pinned source | Attribution is carried by this policy and the dataset manifest | Bytes remain unchanged so published generator/source hashes stay valid |
| Third-party material | Original named source/author | Its own manifest-declared SPDX terms or public-domain statement |
| Generated files and datasets | Generator/capture provenance or `NOASSERTION` where incomplete | Dataset manifests, notices, and retained-environment records govern |

Adding a modern header to an inherited Linux 0.01 file would alter the
archaeological source, invalidate patch identities, and falsely imply original
authorship. Modern adaptations to those files are instead attributable through
Git history, `docs/PORTING_LEDGER.md`, and the versioned patch dataset.

## Automated Gate

`scripts/check-authorship.py` verifies the pinned upstream archive, compares
every tracked or newly added public path with the exact
`docs/AUTHORSHIP-MAP.tsv` manifest, and enforces the appropriate source-header
contract. It rejects project authorship/licenses on inherited, third-party,
generated, or identity-pinned material. Every category comes from an explicit
manifest row. Exact known paths and the verified upstream member list add
non-overridable boundary checks; directory names never classify new files.

Run it directly or through Make:

```bash
make test-authorship
```

New paths must be deliberately classified. The checker fails closed instead of
assuming that a new directory inherits a neighboring license: an absent or
changed manifest row fails the gate.

Published dataset identities take precedence over cosmetic headers. The two
dataset generators and three compiler-case source reductions whose SHA-256
values are embedded in v1 manifests remain byte-stable and receive attribution
through this document, `AUTHORS.md`, Git history, and their dataset metadata.
The reductions are attributed as project-authored reductions derived from Linux
0.01, not as wholly original source.

## Commit Identity

Locally created public commits use
`F E R M I ∞ H A R T <contact@fermihart.com>`. GitHub-generated merge commits
may use the account-linked noreply address; `AUTHORS.md` records that mapping.
No history is rewritten merely to replace an account-generated merge address.

## Boundaries

Authorship is not a substitute for licensing. Attribution of historical text or
quotations does not itself grant redistribution rights. The root `LICENSE` and
`evaluation/v1/THIRD-PARTY-NOTICES.md` remain the controlling engineering
inventory for those boundaries.
