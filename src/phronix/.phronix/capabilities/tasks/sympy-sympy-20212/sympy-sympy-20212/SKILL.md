---
name: sympy-sympy-20212
description: The sympy-sympy-20212 subject.
subject: sympy-sympy-20212
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Handle 0**-oo in Pow |
| `I2` | Instructions | Problem solved |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Add special case for 0**-oo in Pow.__new__ |
| `I5` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints and rules |







## Instructions

### I1 — Handle 0**-oo in Pow

In sympy/core/power.py, add a case in Pow.__new__: if b is S.Zero and e is S.NegativeInfinity, return S.ComplexInfinity. This ensures 0**-oo yields zoo as documented.

### I2 — Problem solved

SymPy incorrectly evaluates `0**-oo` to `0` instead of `ComplexInfinity` (`zoo`).

### I3 — Key idea

Add an explicit conditional for the case where the base is zero and the exponent is negative infinity, returning `ComplexInfinity` as required by SymPy's specifications.

### I4 — Add special case for 0**-oo in Pow.__new__

In `sympy/core/power.py` inside `Pow.__new__`, add a conditional:
```python
elif b is S.Zero and e is S.NegativeInfinity:
    return S.ComplexInfinity
```

### I5 — Instructions to solve it

1. Open `sympy/core/power.py`.
2. Locate the `__new__` method around line 299.
3. After the existing check `elif e == -1 and not b: return S.ComplexInfinity`, add a new branch:
   ```python
   elif b is S.Zero and e is S.NegativeInfinity:
       return S.ComplexInfinity
   ```
4. Save the file and run the test suite to ensure all tests pass.
5. Commit the change.

## Rules

### R1 — Constraints and rules

- Do not alter any existing logic for other exponent cases.
- Preserve the handling of `e == -1 and not b` which already returns `ComplexInfinity`.
- Ensure the new check is placed before the generic autosimplification block to avoid being bypassed.
- All existing regression tests (32) must continue to pass.
- The change must only affect the `Pow.__new__` method in `sympy/core/power.py`.

## References
