---
name: sympy-sympy-15609
description: Fix double subscript issue in LaTeX printer for indexed matrix expressions
subject: sympy-sympy-15609
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve |
| `R1` | Rules | Constraints |





## Instructions

### I1 — Problem description

A LaTeX printer generates a double underscore in indexed matrix expressions, causing compilation errors (e.g., `\sum_{i_{1}=0}^{k - 1} M_{i, _i_1} N_{_i_1, j}`).

### I2 — Key idea

Strip leading underscores from index symbols when generating LaTeX subscripts, because the printer adds an extra underscore for each index, leading to double subscripts.

### I3 — Instructions to solve

1. Open `sympy/printing/latex.py`.
2. Locate the `_print_Indexed` method (around line 614).
3. Replace the existing construction of `tex` with code that strips leading underscores from each index:
```python
idx_strs = [self._print(idx).lstrip('_') for idx in expr.indices]
tex = '{' + tex_base + '}' + '_{' + ','.join(idx_strs) + '}'
```
4. Save the file and run the test suite. The `test_MatrixElement_printing` should now pass, producing LaTeX without double underscores.

## Rules

### R1 — Constraints

- Do not alter the handling of index symbols beyond stripping leading underscores.
- Ensure existing LaTeX rendering for other expressions remains unchanged.
- All regression tests (121) must continue to pass.

## References

- `skill_load(name="sympy-sympy-15609", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

