<!-- Author: F E R M I ∞ H A R T <contact@fermihart.com> -->
<!-- SPDX-License-Identifier: Unlicense -->

# Retained historical source inputs

These are bounded source inputs, not a development-history bundle or new Git
commits. They let the frozen v1 datasets and paired compiler tests run from a
source archive or a new repository without fetching the old repository.

| Original revision | Retained bytes used by |
|---|---|
| `ae458306905d4fee85121ac3c2b42e86ed099310` | Historical core, porting ledger and referenced tests for the v1 patch dataset |
| `86cc23d776e8c7c49061892b1ec4f93f5fb4ad9c` | The three published reduced compiler sources |
| `e6076cb47fd27e1f6ce1b831852a1efe11de99c0` | Pre-Round25 headers, translation units and three ablation inputs |
| `14638cf9deb708680a3c58266bb4c71a865355ea` | The exact inherited console and machine trace payloads |

`MANIFEST.json` retains the full original tree descriptors and original commit
objects, but only the needed file payloads are included in the small archives.
The reader verifies the commit object's exact Git identity, its tree binding,
the reconstructed tree identity, the archive SHA-256, and each retained file's
Git blob identity and mode. A missing payload fails even if its name occurs in
the original tree. No old parent history is fabricated or required.

The trace manifest also retains only the commit/tree objects needed to prove
the two traces' last payload change on their original linear ancestor path.
The reader hash-checks every object and follows the tree path/parent links to
the first actual payload/mode difference. Changing the last-change label or a
proof object fails. This bounded proof does not import the old repository graph
or invent the original capture environment, which remains explicitly incomplete.

The original licenses are retained inside each input archive. The archives are
mixed historical/project source observations, not newly licensed original prose.
The Unlicense comment above covers this explanatory document only. See the
project LICENSE, per-file notices and component inventory for the source rights.

The published v1 datasets and their five identity-pinned source files stay
byte-identical. `scripts/history_inputs.py` adapts only their source-input access;
the frozen patch-generation, comparison and classification algorithms are reused.
Normal checks use `make test-patch-dataset`, `make test-compiler-case-dataset` and
`make test-round25-matrix`. Git remains a host diff/fixture tool, not an unstated
requirement for the old commit graph. Inputs are read locally; no network lookup
or implicit object import occurs.

```sh
python3 scripts/history_inputs.py check
python3 scripts/history_inputs.py patch --check
```

These identities establish consistency with the declared historical snapshots;
they do not authenticate a publisher independently, grant missing rights, or
turn hosted reductions into evidence of guest execution.
