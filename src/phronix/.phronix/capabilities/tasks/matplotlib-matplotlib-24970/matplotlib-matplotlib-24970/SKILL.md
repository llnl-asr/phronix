---
name: matplotlib-matplotlib-24970
description: The matplotlib-matplotlib-24970 subject.
subject: matplotlib-matplotlib-24970
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix NumPy 1.24 deprecation warnings on out-of-bounds integer assignment |
| `R1` | Rules | Signed int conversion preserves semantics for index assignment |

## Instructions

### I1 — Fix NumPy 1.24 deprecation warnings on out-of-bounds integer assignment

**Problem**: When a Colormap receives a small unsigned integer array (uint8, uint16), NumPy 1.24+ raises DeprecationWarning when the code assigns out-of-bounds indices like `self._i_over` (N+1), `self._i_under` (N), or `self._i_bad` (N+2) to the array. These values exceed the range of unsigned types.

**Location**: `lib/matplotlib/colors.py`, Colormap.__call__ method around line 725.

**Solution**: Add an `else` clause after the existing float-type handling to convert non-float integer arrays to signed int before making out-of-bounds assignments:

```python
else:
    # Ensure xa is a signed integer type that can hold out-of-range indices.
    # self._i_over, self._i_under, and self._i_bad are N+1, N, and N+2
    # respectively, which may exceed the range of unsigned integer types.
    xa = xa.astype(int)
```

This converts uint8/uint16 arrays to int64 (signed), allowing assignment of values > 255 without triggering deprecation warnings. The rest of the logic remains unchanged because the subsequent comparisons and assignments work identically on signed int.

**Test**: `lib/matplotlib/tests/test_colors.py::test_get_cmap_builtin` or reproduce with `plt.get_cmap()(np.empty((0, ), dtype=np.uint8))`

## Rules

### R1 — Signed int conversion preserves semantics for index assignment

Converting uint8/uint16 arrays to int (int64) before out-of-bounds index assignments does not change the semantics of the code. The downstream comparisons (xa > self.N - 1, xa < 0) and assignments work identically on signed int because the logic is based on value ranges, not type width. This is a safe rewrite that eliminates NumPy 1.24+ deprecation warnings without altering behavior.

## References
