---
name: sympy-sympy-16503
description: The sympy-pretty-product subject.
subject: sympy-sympy-16503
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix Sum pretty printing alignment |
| `I2` | Instructions | Problem Description |
| `I3` | Instructions | Key Idea |
| `R1` | Rules | Maintain existing pretty printing behavior |




## Instructions

### I1 — Fix Sum pretty printing alignment

Update the `_print_Sum` method in `sympy/printing/pretty/pretty.py` to correctly center the summation expression. Replace the baseline adjustment lines (621‑622) with:

```python
# Center the function pretty form on the sum sign
prettyF.baseline = prettyF.height()//2
```

This ensures the `+` term aligns vertically with the summation variable for both Unicode and ASCII modes. After applying the change, run the relevant pretty‑printing tests for `Sum` to confirm the alignment is correct.

### I2 — Problem Description

Sum pretty printing misaligns the variable and the added constant, causing the `x` and `+ 3` to be offset in the rendered output.

### I3 — Key Idea

Adjust the baseline of the pretty‑printed `F` component so the variable and constant are vertically aligned, using the correct adjustment offset.

## References

- `skill_load(name="sympy-pretty-product", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

## Rules

### R1 — Maintain existing pretty printing behavior

Changes must not break the rendering of other expressions; all regression tests (121) must continue to pass after applying the fix.
