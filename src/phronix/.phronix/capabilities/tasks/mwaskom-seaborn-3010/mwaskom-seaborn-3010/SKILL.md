---
name: mwaskom-seaborn-3010
description: Handle missing data in PolyFit stat to prevent LinAlgError.
subject: mwaskom-seaborn-3010
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Retry with authenticated Docker pull |
| `I2` | Instructions | Ensure phronix tools are invoked |
| `I3` | Instructions | Add missing‑value handling in PolyFit |
| `R1` | Rules | Do not modify unrelated code |
| `R2` | Rules | Maintain test suite integrity |
| `R3` | Rules | Preserve existing regression behaviour |

## Instructions

### I1 — Retry with authenticated Docker pull

Configure Docker credentials or increase rate limits, then rerun the task to pull the required image.

### I2 — Ensure phronix tools are invoked

Add calls to phronix utilities (e.g., skill_write, memory_write) in the agent script before attempting the fix.

### I3 — Add missing‑value handling in PolyFit

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

## Rules

### R1 — Do not modify unrelated code

All changes must be limited to build scripts and Docker configuration; source files of seaborn must remain untouched.

### R2 — Maintain test suite integrity

All existing tests, especially those for `PolyFit`, must continue to pass after the modification.

### R3 — Preserve existing regression behaviour

The change must not alter results when data contain no missing values; the fitted polynomial should be identical to the original implementation.
