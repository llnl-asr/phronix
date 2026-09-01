---
name: sympy-sympy-18532
description: Fix Mod atom extraction edge case
subject: sympy-sympy-18532
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix atoms method to include Atoms and leaf nodes |


## Instructions

### I1 — Fix atoms method to include Atoms and leaf nodes

Update the `atoms` method in `sympy/core/basic.py` to correctly identify leaf objects. Replace the condition:
```python
if isinstance(expr, types) and not expr.args:
    result.add(expr)
```
with a condition that also includes objects that are `Atom` instances:
```python
if isinstance(expr, types) and (expr.is_Atom or not expr.args):
    result.add(expr)
```
This ensures that atomic expressions like `Symbol` are correctly considered leaves, fixing the failing `test_atoms` and `test_sizeof` tests.

## Rules

## References

- `skill_load(name="sympy-sympy-18532", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

