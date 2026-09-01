---
name: matplotlib-matplotlib-24970
description: Skill for matplotlib__matplotlib-24970: NumPy 1.24 deprecation warnings in colormap lookup when array dtype is uint8
subject: matplotlib-matplotlib-24970
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I1 — What problem it solves |
| `I2` | Instructions | I2 — The key idea |
| `I3` | Instructions | I3 — Instructions to solve it |
| `I4` | Instructions | The patch that made the tests pass |
| `R1` | Rules | I4a — Fix one else clause |
| `R2` | Rules | I4b — No other changes to __call__ |
| `R3` | Rules | I4c — Int type guarantee before assignments |
| `R4` | Rules | I4d — Minimal and targeted scope |
| `R5` | Rules | I4e — Preserve existing float-input behavior |
| `R6` | Rules | what problem it solves |
| `R7` | Rules | the key idea |
| `R8` | Rules | instructions to solve it |
| `R9` | Rules | constraints and rules part 1 |
| `R10` | Rules | pitfalls and lessons |

## Instructions

### I1 — I1 — What problem it solves

The symptom a later run would recognise: calling `plt.get_cmap()(np.empty((0,), dtype=np.uint8)` or any colormap call with a uint8-dyped array triggers NumPy 1.24+ deprecation warnings about "NumPy will stop allowing conversion of out-of-bound Python integers to integer arrays." The warnings appear at assignment sites where values that don't fit the current dtype (e.g., assigning `_i_over` = 257 to a uint8 array) are silently converted or warned about. The fix targets the Colormap.__call__ method in lib/matplotlib/colors.py where xa stays as uint8 dtype for non-float inputs, and the later over/under-range assignments attempt to write values outside the uint8 range.

### I2 — I2 — The key idea

When Colormap.__call__ receives a non-float input (like uint8), the xa array stays in that original non-float dtype through the float-handling block (lines 717-727), which only runs for float-type inputs. Later, lines 730-731 assign the sentinel values self._i_over (257) and self._i_under (256) to xa positions that have been validated with np.clip. Since 257 and 256 exceed uint8's max value of 255, NumPy 1.24+ emits a deprecation warning about out-of-bound Python integer-to-array conversion. The single-line fix: after the existing `xa = xa.astype(int)` on line 727, add `else: xa = xa.astype(int)` so that for any non-float input — not just the explicit float path — xa is always the int type before those assignments, preventing the warnings.

### I3 — I3 — Instructions to solve it

In lib/matplotlib/colors.py, locate the Colormap.__call__ method. Find the block after `xa = xa.astype(int)` on line 727 (the line that converts within the float-typo handling). Add an else clause:

    # Avoid converting large positive values to negative integers.
    np.clip(xa, -1, self.N, out=xa)
    xa = xa.astype(int)
    else:
        # Ensure xa is an integer type to avoid NumPy 1.24+
        # deprecation warnings for out-of-bound values.
        xa = xa.astype(int)
# Set the over-range indices before the under-range;
# otherwise the under-range values get converted to over-range.
xa[xa > self.N - 1] = self._i_over

The new `else:` branch ensures that when the input X has a non-float dtype (e.g., uint8, other integer types), xa is immediately and unconditionally converted to the int type before the over/under-range index assignments on the following lines. This prevents the NumPy 1.24+ deprecation warning that occurs when integer values that don't fit the original dtype are assigned to the clipped array. Place the else immediately after the unconditional `xa = xa.astype(int)` so both the float path and non-float paths route through the same int-conversion guarantee.

### I4 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/lib/matplotlib/colors.py b/lib/matplotlib/colors.py
index 2d3072da04..4688ee02c3 100755
--- a/lib/matplotlib/colors.py
+++ b/lib/matplotlib/colors.py
@@ -725,6 +725,10 @@ class Colormap:
                 # Avoid converting large positive values to negative integers.
                 np.clip(xa, -1, self.N, out=xa)
                 xa = xa.astype(int)
+        else:
+            # Ensure xa is an integer type to avoid NumPy 1.24+
+            # deprecation warnings for out-of-bound values.
+            xa = xa.astype(int)
         # Set the over-range indices before the under-range;
         # otherwise the under-range values get converted to over-range.
         xa[xa > self.N - 1] = self._i_over
```

## Rules

### R1 — I4a — Fix one else clause

Add exactly one `else:` clause after `xa = xa.astype(int)` on line 727 in lib/matplotlib/colors.py. No other lines in the __call__ method are changed.

### R2 — I4b — No other changes to __call__

Do not modify the lines that assign xa[xa > self.N - 1] = self._i_over or xa[xa < 0] = self._i_under. Those remain as they were before the fix.

### R3 — I4c — Int type guarantee before assignments

Ensure xa is int type before the over/under-range assignments; self._i_over (257) and self._i_under (256) are Python ints that exceed uint8's max of 255, triggering the NumPy deprecation when assigned to a uint8 array.

### R4 — I4d — Minimal and targeted scope

Keep the change scoped to the single else clause after line 727. Do not combine with broader dtype-conversion refactors.

### R5 — I4e — Preserve existing float-input behavior

The fix preserves all existing behavior for float inputs while eliminating the deprecation warning for non-float dtypes like uint8.

### R6 — what problem it solves

This skill captures the fix for NumPy 1.24+ deprecation warnings in matplotlib's colormap lookup when the input array has uint8 dtype. The issue occurs in Colormap.__call__ method in lib/matplotlib/colors.py: when the input X has non-float dtype (like uint8), the variable xa remains with that dtype after the float-handling block, so lines 730-731 assign values 257 (self._i_over) and 256 (self._i_under) to a uint8 array, triggering NumPy 1.24+ deprecation warnings about "out-of-bound Python integer conversions to integer arrays." The fix adds an else clause after xa = xa.astype(int) to ensure xa is always integer type before the over/under-range index assignments.

### R7 — the key idea

The key idea is that when Colormap.__call__ receives input X with non-float dtype (e.g., uint8), the variable xa retains the original dtype after the float-specific scaling/clip/conversion block (lines 717-727). Since xa stays as uint8, the subsequent assignments at lines 730-731 (xa[xa > self.N - 1] = self._i_over and xa[xa < 0] = self._i_under) attempt to assign values 257 and 256 respectively to a uint8 array, which triggers NumPy 1.24+ deprecation warnings about "NumPy will stop allowing conversion of out-of-bound Python integers to integer arrays." The fix ensures xa is always converted to int type before these assignments by adding an else clause: if the input dtype is not float, convert xa to int just as the float branch does.

### R8 — instructions to solve it

In lib/matplotlib/colors.py, find the Colormap.__call__ method. After line 727 (xa = xa.astype(int)), add an else clause that converts xa to int type for non-float dtypes:

    # Avoid converting large positive values to negative integers.
    np.clip(xa, -1, self.N, out=xa)
    xa = xa.astype(int)
    else:
        # Ensure xa is an integer type to avoid NumPy 1.24+
        # deprecation warnings for out-of-bound values.
        xa = xa.astype(int)
    # Set the over-range indices before the under-range;
    # otherwise the under-range values get converted to over-range.
    xa[xa > self.N - 1] = self._i_over
    xa[xa < 0] = self._i_under

This ensures xa is always int type before the over/under-index assignments, preventing the deprecation warning when self._i_over (257) and self._i_under (256) are assigned to arrays with uint8 or other non-int dtypes.

### R9 — constraints and rules part 1

• Add exactly one `else:` clause after `xa = xa.astype(int)` (line 727 in lib/matplotlib/colors.py). No other lines in the __call__ method are changed.

### R10 — pitfalls and lessons

• Pitfall: When Colormap.__call__ receives non-float X (e.g., uint8 array), xa retains that dtype and the assignments xa[xa > self.N - 1] = self._i_over (value 257) and xa[xa < 0] = self._i_under (value 256) trigger NumPy 1.24+ deprecation warnings about "out-of-bound Python integer conversions to integer arrays." The warning message states "The conversion of 257 to uint8 will fail in the future."
• Lesson: Always ensure xa is int type before the over/under-index assignments in Colormap.__call__. The float-handling block (lines 717-727) already converts to int, but non-float dtypes skip that block. The fix's else clause guarantees consistent int type regardless of input dtype.
• Verification: 1 of 1 target test (test_index_dtype[uint8]) passes with the fix. 253 of 253 regression tests pass. The pre-existing test_double_register_builtin_cmap failure (MatplotlibDeprecationWarning about register_cmap deprecated in Matplotlib 3.7) is unrelated and was documented as such.
