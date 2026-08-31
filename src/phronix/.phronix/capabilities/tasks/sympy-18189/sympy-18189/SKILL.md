---
name: sympy-18189
description: Fix diophantine symbol ordering issue with permute=True
subject: sympy-18189
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Problem it solves |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instruction 1 |
| `I5` | Instructions | Instruction 2 |
| `R1` | Rules | Constraint |






## Instructions

### I1 — Problem description

Sympy's diophantine reorders solution tuples based on `syms` even when `permute=True`, causing inconsistent results.

### I2 — Problem it solves

Fails when `diophantine(..., permute=True)` returns incomplete or order‑dependent solution sets due to the `syms` argument influencing tuple ordering.

### I3 — Key idea

When `permute=True`, the solution tuple order must be based solely on the sorted variable list, ignoring any custom `syms` ordering.

### I4 — Instruction 1

In `sympy/solvers/diophantine.py` locate the block handling `syms` around line 174.
Replace the existing handling with:
```python
if syms:
    if not is_sequence(syms):
        raise TypeError('syms should be given as a sequence, e.g. a list')
    # Filter to symbols present in the equation
    syms = [i for i in syms if i in var]
    # When permute=True ignore custom ordering; use sorted `var`
    # (no reordering of the result tuples)
```

### I5 — Instruction 2

Ensure recursive `diophantine` calls propagate the `permute` flag.
Replace the line:
```python
return {tuple([t[dict_sym_index[i]] for i in var]) for t in diophantine(eq, param)}
```
with:
```python
return {tuple([t[dict_sym_index[i]] for i in var]) for t in diophantine(eq, param, permute=permute)}
```

## Rules

### R1 — Constraint

Do not modify any other logic in `diophantine.py`; changes must be limited to handling of `syms` and propagation of `permute`.

## References

- `skill_load(name="sympy-18189", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
