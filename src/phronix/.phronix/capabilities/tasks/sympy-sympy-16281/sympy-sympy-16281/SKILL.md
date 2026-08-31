---
name: sympy-sympy-16281
description: The sympy-sympy-16281 subject.
subject: sympy-sympy-16281
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem it solves |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints and rules |





## Instructions

### I1 — Problem it solves

Pretty‑printing of `Product` displays an extra empty line and overly wide bars, causing asymmetric and visually bulky output for infinite products.

### I2 — Key idea

The visual representation of `Product` should avoid an empty line below the horizontal bar and keep the width comparable to `Sum` by trimming unnecessary padding.

### I3 — Instructions to solve it

1. Open `sympy/printing/pretty/pretty.py` (or the relevant pretty‑printer module).
2. Locate the function that renders `Product` objects, typically `pretty_product`.
3. Remove the final newline that is appended after drawing the horizontal bar.
4. Adjust the bar‑width calculation to use the maximum width of the upper and lower parts, trimming any extra padding so the total width matches that of `Sum` for comparable limits.
5. Add a regression test in `sympy/printing/tests/test_pretty.py` asserting that the printed output for `Product(1, (n, 1, oo))` does not contain a trailing empty line and that the width is not greater than the `Sum` representation for the same limits.
6. Run the new test only (`pytest sympy/printing/tests/test_pretty.py::test_product`) to verify the fix.
7. Commit the changes.

## Rules

### R1 — Constraints and rules

- Do not alter the rendering of other expression types (e.g., Sum, Integral).
- Preserve existing Unicode output for `Product` when `use_unicode=True`.
- Ensure existing tests for pretty printing continue to pass.
- Changes must be backward compatible with SymPy's public API.
- The width calculation must not break alignment for nested products.

## References

- `skill_load(name="sympy-sympy-16281", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

