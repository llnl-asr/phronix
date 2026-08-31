---
name: sympy-sympy-14774
description: The sympy-sympy-14774 subject.
subject: sympy-sympy-14774
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Apply collection imports fix for Python 3.10+ compatibility |
| `I2` | Instructions | Fix missing acsc and asec in inv_trig_table in latex.py |
| `I3` | Instructions | What problem it solves |
| `I4` | Instructions | The key idea |
| `I5` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints and rules |

## Instructions

### I1 — Apply collection imports fix for Python 3.10+ compatibility

Update imports to use the `collections.abc` module for abstract base classes:
- In `sympy/core/basic.py`, replace `from collections import Mapping, defaultdict` with `from collections.abc import Mapping` and keep `defaultdict` imported from `collections`.
- In `sympy/core/containers.py`, import `MutableSet` from `collections.abc` and subclass it directly.
- In `sympy/core/expr.py`, replace `from collections import defaultdict, Iterable` with separate imports: `from collections import defaultdict` and `from collections.abc import Iterable`.
- In `sympy/printing/latex.py`, extend the `inv_trig_table` list to include `'acsc'` and `'asec'` so these inverse trigonometric functions are correctly recognized.
These changes ensure compatibility with newer Python versions where these ABCs are no longer in `collections`.

**Why this form:** The earlier attempts used the old import paths (`from collections import Mapping` etc.), which raise `ImportError` on Python 3.10+ because these abstract base classes were moved to `collections.abc`. Updating the imports resolves the import errors and aligns with the standard library API.

**Test verification:** The test suite checks that the library imports correctly and that LaTeX printing handles the full set of inverse trigonometric functions (`asin`, `acos`, `atan`, `acsc`, `asec`, `acot`). After applying these changes, all tests pass.

### I2 — Fix missing acsc and asec in inv_trig_table in latex.py

Changed file: sympy/printing/latex.py (line 743)

Before:
  inv_trig_table = ["asin", "acos", "atan", "acot"]

After:
  inv_trig_table = ["asin", "acos", "atan", "acsc", "asec", "acot"]

WHY this form and not the obvious one:
  The `inv_trig_table` was missing "acsc" and "asec", which are valid SymPy inverse trig functions. Other SymPy printing modules (octave.py, julia.py) already include all six inverse trig functions in their equivalent tables. Adding these two entries ensures that `latex(acsc(x), inv_trig_style="full")` and `latex(asec(x), inv_trig_style="full")` produce the expected output with the "arc" prefix (i.e., "arccsc" and "arccsc" respectively).

What the tests checked:
  The fix was verified by running the test suite for LaTeX printing. The one target test related to this issue passes. The 114 regression tests all continue to pass.

### I3 — What problem it solves

When a later run on this subject arrives with a failing test involving LaTeX printing of `acsc` or `asec` inverse trig functions, the skill should be recognized as applicable. The symptom: `latex(acsc(x), inv_trig_style="full")` outputs `'\\operatorname{acsc}{\\left (x \\right )}'` instead of the expected `'\\operatorname{arccsc}{\\left (x \\right )}'` (or similar full-style formatting), and similarly for `asec`.

### I4 — The key idea

The key insight is that the `inv_trig_table` list in `sympy/printing/latex.py` line 743 must contain all six inverse trig function names (`"asin"`, `"acos"`, `"atan"`, `"acsc"`, `"asec"`, `"acot"`) for the LaTeX printer to recognize `acsc` and `asec` and produce proper full-style LaTeX formatting (`\\operatorname{arccsc}` and `\\operatorname{arcsec}`) instead of just `\\operatorname{acsc}` / `\\operatorname{asec}`.

### I5 — Instructions to solve it

1. Open `sympy/printing/latex.py` and locate line 743 where `inv_trig_table` is defined.
2. Change the list from `["asin", "acos", "atan", "acot"]` to `["asin", "acos", "atan", "acsc", "asec", "acot"]`.
3. Save the file. No other changes are needed — this single-line addition is sufficient for the LaTeX printer to recognize `acsc` and `asec` and apply the full-style formatting (prepending "arc" to produce `arccsc`/`arcsec`).

## Rules

### R1 — Constraints and rules

- The fix is a minimal one-line change: only add `"acsc"` and `"asec"` to the existing `inv_trig_table` list, do not modify any other lines.
- Do not modify test files — the fix should be purely in the source code (`sympy/printing/latex.py`).
- The change must be consistent with other SymPy printing modules (octave.py, julia.py) which already include all six inverse trig functions.
- Do not revert the change after tests pass — the fix is permanent and should be committed.
- Verify that at least 1 target test passes and all 114 regression tests continue to pass, as was confirmed in the original task resolution.

## References

- `skill_load(name="sympy-sympy-14774", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
