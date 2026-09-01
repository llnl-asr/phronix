---
name: sympy-sympy-19254-mignotte-fix
description: Fix the isqrt import path in Mignotte bound functions
subject: sympy-sympy-19254-mignotte-fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | fix-mignotte-isqrt-import |


## Instructions

### I1 — fix-mignotte-isqrt-import

Replace `from sympy import isqrt` with `from sympy.core.power import isqrt` in both `dup_zz_mignotte_bound` and `dmp_zz_mignotte_bound` functions in sympy/polys/factortools.py, so that the integer square root import works correctly.

## Rules

## References

- `skill_load(name="sympy-sympy-19254-mignotte-fix", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

