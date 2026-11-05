# Reduced compiler cases v1

This directory is the versioned reference-run dataset for the three reduced
`-O2`-sensitive patterns investigated in Waves 075-083. It retains the exact
source snapshots, one GCC 13.3.0 observation grid, compiler-generated assembly,
hosted executables, process output, classifications, and environment identities.

## Observation grid

The reference run contains 18 cells: three reductions, `-O0`/`-O1`/`-O2`, and
two hosted GNU/Linux process ABIs (`x86_64` SysV and `i386` SysV). Seventeen
cells pass. Only `bitmap_inline_asm` at `x86_64 -O2` fails, with exit status 1
and the retained `bit 0 not visible` diagnostic.

The i386 programs were compiled against the five Debian/Ubuntu package archives
identified in `environment.json` and executed through the identified i386 glibc
loader. `${CC}`, `${MULTILIB_ROOT}`, and `${DATASET_ROOT}` in argv arrays are
path bindings; replacing them with the identified compiler, extracted package
root, and dataset root reconstructs the actual process argv without retaining
ephemeral absolute paths.

## Evidence boundaries

This is one compiler identity, not a compiler-version matrix. Both ABIs are
hosted GNU/Linux process ABIs, not the freestanding Linux 0.01 kernel ABI. The
dataset does not prove that any `-O1` workaround is necessary or minimal, does
not establish a GCC bug, and does not reproduce the unobserved historical
symptoms for `buffer_freelist` or `vsprintf_percent_s`.

Comments inside the source snapshots are inherited investigation hypotheses,
not evidence-linked conclusions. In particular, the bitmap source comment that
the asm does not mention memory is inaccurate: its memory operand is input-only,
and its statement about full-kernel effects is untested by this dataset. The
bounded conclusions are in `classifications.json`; where the run does not
establish a proposition, the dataset uses `NOT_ESTABLISHED` rather than a
boolean `false`.

## Files

- `MANIFEST.json`: identity, scope, counts, source provenance, and non-claims.
- `environment.json`: compiler, tools, host, ABI runtime, and package identities.
- `observations.jsonl`: normalized argv, return codes, stdout/stderr, and payload hashes.
- `classifications.json`: bounded conclusions linked to observation IDs.
- `sources/`: exact reductions from the pinned source commit.
- `assembly/`: full compiler-generated assembly for every cell, with the
  ephemeral multilib-root prefix replaced by `${MULTILIB_ROOT}` in comments and
  trailing horizontal whitespace removed.
- `binaries/`: the exact hosted executables that produced the retained outputs.
- `SHA256SUMS.txt`: every non-self-referential file in this directory.

Regenerate a candidate outside this immutable publication with:

```sh
python3 scripts/build-compiler-case-dataset.py   --compiler /usr/bin/gcc-13   --multilib-packages /path/to/package-archives
```
