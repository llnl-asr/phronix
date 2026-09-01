---
name: matplotlib-matplotlib-22835
description: The matplotlib-matplotlib-22835 subject.
subject: matplotlib-matplotlib-22835
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Instructions |
| `R1` | Rules | Constraints |





## Instructions

### I1 — Problem

format_cursor_data crashes with BoundaryNorm because it is not invertible, and the fallback returns values with extra precision (e.g., "[-1.]" instead of "[-1.0]") causing target test failures.

### I2 — Key Idea

The crash can be avoided with a try/except, but the fallback must preserve numeric precision to match expected test output.

### I3 — Instructions

1. Open `lib/matplotlib/artist.py`.
2. Locate the `format_cursor_data` method around line 1300.
3. Replace the existing `try/except` block with:
```python
try:
    neighbors = self.norm.inverse(
        (int(self.norm(data) * n) + np.array([0, 1])) / n)
except ValueError:
    # BoundaryNorm is not invertible; return the formatted value with the same precision as the original normed value.
    normed_val = self.norm(data)
    # Use `cbook._g_sig_digits` to match the original formatting precision.
    g_sig_digits = cbook._g_sig_digits(data, normed_val)
    fmt = f"{{:.{g_sig_digits}g}}"
    neighbors = np.array([fmt.format(normed_val), fmt.format(normed_val)])
```
4. Ensure the import `import numpy as np` is present.
5. Run the test suite; the target test `test_format_cursor_data_BoundaryNorm` should now pass, and all regression tests remain green.

## Rules

### R1 — Constraints

- Do not alter the precision formatting of other scalar values.
- Regression tests (24) must continue to pass.
- The fallback must handle non‑invertible norms without raising exceptions.
- Preserve the original numeric precision expected by the target test (e.g., "[-1.0]").

## References

- `skill_load(name="matplotlib-matplotlib-22835", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

