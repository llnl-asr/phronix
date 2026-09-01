---
name: solution-sympy-sympy-19254-reconcile
description: Fix dup_zz_mignotte_bound implementation
subject: solution-sympy-sympy-19254-reconcile
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix dup_zz_mignotte_bound bound |


## Instructions

### I1 — Fix dup_zz_mignotte_bound bound

Replace the doubled Mignotte bound with the correct implementation: compute the original bound `K.sqrt(K(n + 1))*2**n*a*b` and return it directly, removing the extra factor of 2. This restores the expected test value (6) for `dup_zz_mignotte_bound(2*x**2 + 3*x + 4)`.

## Rules

## References

- `skill_load(name="solution-sympy-sympy-19254-reconcile", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

