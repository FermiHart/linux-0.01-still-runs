# Upstream bug-report template for compiler cases

This template is used when a case is classified as `GCC_BUG`.  As of the
classification run documented in `CLASSIFICATION.md`, **no case is classified
as a GCC bug**: `bitmap_inline_asm` is undefined behavior in the source, and the
other two cases could not be reproduced in isolation on the tested toolchain.

When a future compiler-version matrix (Wave 082) reproduces a failure that is
not explainable as source undefined behavior, use the template below and
attach the corresponding `summary.json`, assembly diff, and audit log.

---

**Component:** c
**Summary:** GCC `-O2` miscompiles `<case-name>` pattern from Linux 0.01
**Version tested:** <compiler-version>
**Host:** <host-arch>

**Description:**
The attached minimal reproducer `<case>.c` behaves correctly at `-O0` and
`-O1` but fails at `-O2`.  The source does not contain strict-aliasing
violations, sequence-point ambiguities, or signed-overflow undefined behavior.
The generated `-O2` assembly (see `build/asm/<case>-<abi>-O2.asm`) differs
from `-O1` in the following observable way: <insert difference>.

**Steps to reproduce:**
```bash
cd tests/compiler-cases
make clean run CC=<compiler>
./build/<case>-<abi>-O2
```

**Expected result:** <expected output>
**Observed result:** <observed output>

**Attachments:**
- `<case>.c`
- `build/summary.json`
- `build/asm/<case>-<abi>-O0.asm`, `-O1.asm`, `-O2.asm`
- `build/asm/<case>-<abi>-O1-vs-O2.diff`
- `build/audit.txt`
