---
name: sympy-21627
description: The sympy-21627 subject.
subject: sympy-21627
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | RecursionError guard for Factors.is_zero |
| `I2` | Instructions | Safe modulo check in hyperbolic._eval_is_real |



## Instructions

### I1 — RecursionError guard for Factors.is_zero

In `sympy/core/exprtools.py`, modify `Factors.is_zero` to:
```python
try:
    f = self.factors
    return len(f) == 1 and S.Zero in f
except RecursionError:
    return False
```

### I2 — Safe modulo check in hyperbolic._eval_is_real

In `sympy/functions/elementary/hyperbolic.py`, modify `_eval_is_real` to:
```python
re, im = arg.as_real_imag()
try:
    return (im % pi).is_zero
except Exception:
    return False
```

## Rules

## References
