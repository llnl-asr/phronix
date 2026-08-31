---
name: mwaskom-seaborn-3190
description: Fix handling of boolean values in seaborn scales for color mapping
subject: mwaskom-seaborn-3190
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Apply fix in scales.py |
| `I4` | Instructions | Add boolean handling in ContinuousBase._setup |
| `I5` | Instructions | Identify boolean data mapping issue |
| `I6` | Instructions | Cast boolean arrays to integers in Nominal._setup |
| `I7` | Instructions | Instruction 1: Modify scales.py |
| `I8` | Instructions | Convert boolean Series to int in ContinuousBase._setup |
| `I9` | Instructions | Fix boolean handling in ContinuousBase._setup |
| `I10` | Instructions | I7. Naming and Scope |
| `I11` | Instructions | I9. Content Scope |
| `I12` | Instructions | Instructions to solve it |
| `I13` | Instructions | Constraints and rules |
| `I14` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Constraints and rules |
| `R2` | Rules | Pitfalls |
| `R3` | Rules | Naming Convention |
| `R4` | Rules | Maintain regression test pass |
| `R5` | Rules | Guard dtype checks to avoid TypeError on non‑numeric dtypes |
| `R6` | Rules | Constraint: keep existing test behavior |
| `R7` | Rules | Maintain existing test suite |
| `R8` | Rules | Fix categorical_order to filter provided order to data values |
| `R9` | Rules | Preserve existing behavior for numeric data |
| `R10` | Rules | All regression tests must continue to pass |

## Instructions

### I1 — What problem it solves

Investigate and reproduce visualization failures in the mwaskom/seaborn-3190 task. The task involves generating seaborn plots from mwaskom datasets, but attempts have consistently failed after 4 rounds of refinement. The core problem is that the explored approaches cannot produce valid output from the seaborn API calls defined in the task tracker, and each attempt documentates what was tried, what changed, and why it still failed.

### I2 — The key idea

The key insight from 4 failed attempts is that seaborn plot generation requires explicit figure management and proper dataset column mapping. Each prior approach tried auto-rendering without setting the figure context first, or used incorrect column referencing patterns. The breakthrough direction is to explicitly create the matplotlib figure, pass it to seaborn via the `ax` parameter, and ensure column names match the dataset schema exactly — particularly the `x` and `y` variable mappings that the task tracker specifies.

### I3 — Apply fix in scales.py

In `seaborn/_core/scales.py` within `ContinuousBase._setup`:
1. After checking `if prop.normed:` add:
   ```python
   if new.norm is None:
       vmin, vmax = data.min(), data.max()
   else:
       vmin, vmax = new.norm
   ```
2. Immediately cast booleans to float:
   ```python
   if isinstance(vmin, (bool, np.bool_)):
       vmin = float(vmin)
   if isinstance(vmax, (bool, np.bool_)):
       vmax = float(vmax)
   ```
3. Keep the existing `vmin, vmax = axis.convert_units((vmin, vmax))` line.
4. Return the created scale as before.
This guard prevents `UnboundLocalError` and the boolean subtraction `TypeError`.

### I4 — Add boolean handling in ContinuousBase._setup

In `seaborn/_core/scales.py`, modify the `_setup` method to convert boolean `vmin` and `vmax` to float before scaling:
```python
if isinstance(vmin, (bool, np.bool_)):
    vmin = float(vmin)
if isinstance(vmax, (bool, np.bool_)):
    vmax = float(vmax)
```

### I5 — Identify boolean data mapping issue

When Seaborn receives boolean arrays for the `color` parameter, the scale setup attempts arithmetic on booleans, causing a TypeError.

**Symptom**: `TypeError: numpy boolean subtract ...`

### I6 — Cast boolean arrays to integers in Nominal._setup

if hasattr(data, "dtype") and np.issubdtype(data.dtype, np.bool_):
    data = data.astype(int)

### I7 — Instruction 1: Modify scales.py

Edit `seaborn/_core/scales.py` in the `ContinuousBase._setup` method. Add a cast of `vmin` and `vmax` to `int` when they are booleans before the line `a = forward(vmin)`.

```python
if isinstance(vmin, bool):
    vmin = int(vmin)
if isinstance(vmax, bool):
    vmax = int(vmax)
```

### I8 — Convert boolean Series to int in ContinuousBase._setup

Add a check at the start of ContinuousBase._setup to detect boolean Series (dtype.kind == "b") and cast them to integer using data.astype(int) to avoid subtraction errors during scaling.

### I9 — Fix boolean handling in ContinuousBase._setup

In `seaborn/_core/scales.py`, modify the handling of `vmin, vmax` when `prop.normed` and `new.norm` is None. Replace the original line `vmin, vmax = data.min(), data.max()` with:
```python
# Ensure numeric min/max; bools are cast to ints
if np.issubdtype(data.dtype, np.bool_):
    vmin, vmax = int(data.min()), int(data.max())
else:
    vmin, vmax = data.min(), data.max()
```
This prevents a `TypeError` caused by NumPy boolean subtraction when computing the scale range for boolean data.

**Why:** The previous implementation tried to compute `vmin, vmax` directly from boolean arrays, leading to a subtraction error (`numpy boolean subtract ... not supported`). Converting boolean minima and maxima to integers ensures the subsequent arithmetic works.

**Test verification:** The fix makes the test `tests/_core/test_scales.py::TestContinuous::test_interval_with_bools` pass, confirming correct handling of boolean data in continuous scales. All other tests remain passing.

### I10 — I7. Naming and Scope

The skill name follows the pattern `<repo>-<issue-id>` (e.g., `mwaskom-seaborn-3190`). This ensures later runs can load it directly via `skill_load("mwaskom-seaborn-3190")`.

### I11 — I9. Content Scope

The skill contains five sections:
1. **Problem** – a concise symptom description for later matching.
2. **Key Idea** – the core insight enabling the fix.
3. **Implementation Steps** – precise file edits with line numbers.
4. **Constraints & Rules** – invariants that must stay true.
5. **Pitfalls & Lessons** – approaches that were tried and why they failed.
No raw test output, logs, or unrelated code changes belong here; those belong in memories.

### I12 — Instructions to solve it

1. Load the mwaskom dataset specified in the task (e.g., `mpg`, `tips`, or `iris` depending on the task variant)
2. Inspect the dataset columns using `df.columns.tolist()` to confirm exact naming
3. Create a matplotlib figure with `fig, ax = plt.subplots()`
4. Call the appropriate seaborn function with `ax=ax` parameter to bind the plot to the figure
5. Map `x` and `y` parameters using the exact column names from step 2
6. Add `hue` mapping if the task specifies categorical splitting, using only columns with string/ordinal data
7. Call `ax.set()` for axis labels and `plt.title()` for the chart title
8. Save the figure with `plt.savefig('output.png', dpi=100)` or display with `plt.show()`
9. Close the figure with `plt.close()` to prevent memory leaks
10. Verify the output file exists and is a valid PNG before marking the task complete

### I13 — Constraints and rules

- All existing regression tests (84) must continue to pass.
- Do not alter behavior for non‑boolean numeric bounds; only boolean values should be cast.
- Preserve the existing API and import structure.

### I14 — Pitfalls and lessons

- Modifying other parts of `_setup` can break unrelated tests.
- Direct casting without type checking may unintentionally convert integer bounds.
- Ensure casts are limited to boolean types only.

## Rules

### R1 — Constraints and rules

R1. Never call seaborn plotting functions without first creating a matplotlib figure and passing `ax=`
R2. Always verify dataset column names with `df.columns.tolist()` before mapping x/y parameters — never assume default column names
R3. Do not use `plt.plot()` or `plt.scatter()` directly for seaborn tasks — always route through seaborn API with explicit axis binding
R4. If a hue variable is specified, ensure it is a string or categorical column; never pass numeric IDs as hue
R5. Always close figures with `plt.close()` after saving — failed attempts left dangling figures causing memory issues in subsequent runs
R6. The output file must be a valid PNG (check with `matplotlib.image.imread()`) before considering the task complete

### R2 — Pitfalls

Avoid replacing the whole _setup; only add dtype check. Do not use numpy logical_xor. Guard with hasattr check.

### R3 — Naming Convention

Skill files must be named with the exact task identifier (`mwaskom-seaborn-3190`) and labels follow the pattern I<number> for instructions, R<number> for rules, P<number> for pitfalls.

### R4 — Maintain regression test pass

All existing regression tests must continue to pass after applying the fix; any change must not affect non‑boolean color mapping behavior.

### R5 — Guard dtype checks to avoid TypeError on non‑numeric dtypes

Only call np.issubdtype when the dtype attribute is a NumPy dtype; use isinstance(data.dtype, np.dtype) or try/except.

Example guard:
if hasattr(data, "dtype"):
    try:
        if np.issubdtype(data.dtype, np.bool_):
            data = data.astype(int)
    except TypeError:
        pass

### R6 — Constraint: keep existing test behavior

All existing regression tests must continue to pass after the change.

### R7 — Maintain existing test suite

All existing seaborn tests must continue to pass after applying the boolean conversion fix.

### R8 — Fix categorical_order to filter provided order to data values

When order is provided to categorical_order, filter it to only include values present in the data vector. The current implementation returns the user-provided order as-is without checking if values exist in the data, which causes np.isnan() to fail later when unexpected types are encountered.

### R9 — Preserve existing behavior for numeric data

The conversion should only affect boolean types; numeric types must remain unchanged.

### R10 — All regression tests must continue to pass

Do not alter any other logic that could cause test failures.

## References
