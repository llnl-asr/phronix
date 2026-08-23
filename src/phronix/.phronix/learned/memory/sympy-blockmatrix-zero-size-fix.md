---
name: sympy-blockmatrix-zero-size-fix
description: Fixed BlockMatrix row/col size handling for Zero elements
metadata:
  type: project
---

Implemented robust `rowblocksizes` and `colblocksizes` properties in `sympy/matrices/expressions/blockmatrix.py` to handle `Zero` objects lacking `.rows`/`.cols`. The methods now infer missing dimensions from other blocks in the same row or column, raising a clear error if undeterminable. All tests now pass (190 passed, 4 xfailed). This ensures block matrix multiplication works correctly when ZeroMatrix simplifications produce `Zero` scalar entries.

**Why:** The original implementation assumed all block entries have `.rows` and `.cols` attributes, causing AttributeError for `Zero` objects during block matrix multiplication, especially for repeated multiplication of block matrices containing ZeroMatrix blocks. The fix adds defensive checks and inference, preventing crashes.

**How to apply:** No further code changes needed; the patched methods now correctly compute sizes for blocks with scalar zeros. This resolves the issue described in `issue.md` where multiplying a BlockMatrix containing ZeroMatrix blocks twice raised an exception.

[[sympy-blockmatrix-zero-size-fix]] refers to this fix's memory for reference.
