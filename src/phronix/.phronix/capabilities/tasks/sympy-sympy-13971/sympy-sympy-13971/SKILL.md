---
name: sympy-sympy-13971
description: Fix LaTeX SeqFormula bracket escaping bug in sympy printing
subject: sympy-sympy-13971
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify the LaTeX printer function for SeqFormula |
| `I2` | Instructions | Modify bracket rendering |
| `I3` | Instructions | Convert slice results to list |
| `I4` | Instructions | Add comment for Jupyter compatibility |
| `I5` | Instructions | Run targeted tests |
| `I6` | Instructions | Render SeqFormula with plain brackets |
| `I7` | Instructions | Fix SeqFormula LaTeX bracket escaping |
| `R1` | Rules | Preserve existing LaTeX functionality |
| `R2` | Rules | Maintain test suite integrity |
| `R3` | Rules | Do not modify test files |
| `R4` | Rules | Keep regression tests passing |

## Instructions

### I1 — Identify the LaTeX printer function for SeqFormula

Open `sympy/printing/latex.py` and locate the `_print_SeqFormula` method.

### I2 — Modify bracket rendering

Change the return statement to use plain brackets `[` and `]` instead of `\left[` and `\right]`. For example, replace `return r"\left[" + ... + r"\right]"` with `return "[" + ... + "]"`.

### I3 — Convert slice results to list

If the method converts slices to tuples, change the conversion to `list(slice_obj)` to avoid tuple handling issues.

### I4 — Add comment for Jupyter compatibility

Add a comment above the method explaining that the change is to make the output render correctly in Jupyter notebooks.

### I5 — Run targeted tests

Execute the tests `test_latex_sequences` and any related symbol tests to ensure no regressions.

### I6 — Render SeqFormula with plain brackets

In `sympy/printing/latex.py` modify `_print_SeqFormula` to return a string with plain brackets `[` and `]` instead of `\left[` and `\right]`. Convert slice results to a list before formatting.
```python
def _print_SeqFormula(self, expr):
    seq = expr.sequence
    if isinstance(seq, slice):
        seq = list(expr.function(*seq.args))
    return f'[{latex(seq)}]'
```
Run `test_latex_sequences` to verify the output matches `[0, 1, 4, 9, \ldots]`.

### I7 — Fix SeqFormula LaTeX bracket escaping

Change r"\left\[ to r"\left[" and r"\right\]" to r"\right]" in the _print_SeqFormula function in sympy/printing/latex.py. This removes the LaTeX display math delimiters (\[ and \]) that were causing bracket escaping issues in Jupyter rendering, replacing them with plain bracket characters [ and ] that render correctly.

## Rules

### R1 — Preserve existing LaTeX functionality

Do not alter other LaTeX printer methods; only modify `_print_SeqFormula`.

### R2 — Maintain test suite integrity

All existing tests must continue to pass after the change.

### R3 — Do not modify test files

Only modify source code in sympy/printing/latex.py. Do not change any test files. The fix must be limited to the two-line change in _print_SeqFormula.

### R4 — Keep regression tests passing

All 102 regression tests must continue passing after the fix. If any regression test fails, the fix is too broad and must be narrowed. Only the _print_SeqFormula function may be modified.

## References

- `skill_load(name="sympy-sympy-13971", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
