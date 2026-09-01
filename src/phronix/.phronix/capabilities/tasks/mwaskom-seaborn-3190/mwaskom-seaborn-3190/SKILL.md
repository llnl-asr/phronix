---
name: mwaskom-seaborn-3190
description: Fix handling of boolean values in seaborn scales for color mapping
subject: mwaskom-seaborn-3190
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add boolean handling in ContinuousBase._setup |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Preserve existing behavior for numeric data |
| `R2` | Rules | All regression tests must continue to pass |

## Instructions

### I1 — Add boolean handling in ContinuousBase._setup

In `seaborn/_core/scales.py`, modify the `_setup` method to convert boolean `vmin` and `vmax` to float before scaling:
```python
if isinstance(vmin, (bool, np.bool_)):
    vmin = float(vmin)
if isinstance(vmax, (bool, np.bool_)):
    vmax = float(vmax)
```

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/seaborn/_core/scales.py b/seaborn/_core/scales.py
index 6c9ecbc9..4cde618a 100755
--- a/seaborn/_core/scales.py
+++ b/seaborn/_core/scales.py
@@ -347,6 +347,11 @@ class ContinuousBase(Scale):
             else:
                 vmin, vmax = new.norm
             vmin, vmax = axis.convert_units((vmin, vmax))
+            # Ensure booleans are treated as numeric for scaling
+            if isinstance(vmin, (bool, np.bool_)):
+                vmin = float(vmin)
+            if isinstance(vmax, (bool, np.bool_)):
+                vmax = float(vmax)
             a = forward(vmin)
             b = forward(vmax) - forward(vmin)
```

## Rules

### R1 — Preserve existing behavior for numeric data

The conversion should only affect boolean types; numeric types must remain unchanged.

### R2 — All regression tests must continue to pass

Do not alter any other logic that could cause test failures.
