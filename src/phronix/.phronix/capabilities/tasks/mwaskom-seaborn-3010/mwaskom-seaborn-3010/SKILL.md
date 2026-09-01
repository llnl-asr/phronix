---
name: mwaskom-seaborn-3010
description: Handle missing data in PolyFit stat to prevent LinAlgError.
subject: mwaskom-seaborn-3010
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add missing‑value handling in PolyFit |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Preserve existing regression behaviour |
| `R2` | Rules | Maintain test suite integrity |

## Instructions

### I1 — Add missing‑value handling in PolyFit

Edit `seaborn/_stats/regression.py`:
1. Import pandas if not already imported.
2. Inside `PolyFit.__call__`, after extracting `x` and `y`, insert:
   ```python
   mask = x.notna() & y.notna()
   x_clean = x[mask]
   y_clean = y[mask]
   ```
3. Replace the uniqueness check with `if x_clean.nunique() <= self.order:` and keep the fallback `xx = yy = []`.
4. In the fitting branch, call `np.polyfit(x_clean, y_clean, self.order)` and generate `xx` with `np.linspace(x_clean.min(), x_clean.max(), self.gridsize)`.
5. Return the DataFrame as before.
```

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/seaborn/_stats/regression.py b/seaborn/_stats/regression.py
index 7b7ddc8..04100cc 100755
--- a/seaborn/_stats/regression.py
+++ b/seaborn/_stats/regression.py
@@ -23,7 +23,11 @@ class PolyFit(Stat):
 
         x = data["x"]
         y = data["y"]
-        if x.nunique() <= self.order:
+        # Drop rows with NaN values before fitting
+        df = pd.DataFrame({"x": x, "y": y}).dropna()
+        x = df["x"]
+        y = df["y"]
+        if len(x) <= self.order:
             # TODO warn?
             xx = yy = []
         else:
```

## Rules

### R1 — Preserve existing regression behaviour

The change must not alter results when data contain no missing values; the fitted polynomial should be identical to the original implementation.

### R2 — Maintain test suite integrity

All existing tests, especially those for `PolyFit`, must continue to pass after the modification.
