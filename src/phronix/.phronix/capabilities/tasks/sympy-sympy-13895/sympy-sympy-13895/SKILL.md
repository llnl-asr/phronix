---
name: sympy-sympy-13895
description: Lesson about proper integration point for UniqueConstraint field validation in Django models.
subject: sympy-sympy-13895
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Refine real_root handling to preserve real results only when safe |
| `I2` | Instructions | Problem description |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Add real_root handling for negative bases with rational exponents |





## Instructions

### I1 — Refine real_root handling to preserve real results only when safe

In `sympy/simplify/powsimp.py` within `_denest_pow`, replace the unconditional `real_root` block with a conditional that checks the realness of the root before applying it:

```python
_, be = b.as_base_exp()
# Use real_root for negative numeric bases with rational exponents only if the root is real
if b.is_Number and b.is_negative and be.is_Rational:
    root = real_root(b, be.q)
    if root.is_real:
        return root ** be.p
# Fallback to existing handling (which may return a complex result)
```

This ensures that `real_root` is only used when it yields a real value, avoiding the regression in tests `test_powers_Integer` and `test_issue_13890`.

### I2 — Problem description

Simplify expression (-x/4 - 1/12)**x - 1 produces a result that is not equivalent to the original expression, causing test failures in `test_issue_13890` and `test_powers_Integer`.

### I3 — Key idea

Handle negative numeric bases with rational exponents using real_root to keep results real, avoiding complex results from standard power handling.

### I4 — Add real_root handling for negative bases with rational exponents

In `sympy/simplify/powsimp.py` inside function `_denest_pow`, after unpacking the base and exponent, insert:

```python
    from sympy import real_root
    if b.is_Number and b.is_negative and be.is_Rational:
        return real_root(b, be.q) ** be.p
```

This ensures negative numeric bases with rational exponents are evaluated via `real_root` to keep results real.

## Rules

## References

- `skill_load(name="django-unique-constraint-field-check", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

