---
name: sympy-core-sympify
description: Fix conversion of numpy floating types to SymPy Float.
subject: sympy-core-sympify
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix numpy float conversion in _convert_numpy_types |
| `I2` | Instructions | Update _convert_numpy_types to use a.item() |
| `I3` | Instructions | Update _convert_numpy_types |
| `I4` | Instructions | Patch sympify.py |





## Instructions

### I1 — Fix numpy float conversion in _convert_numpy_types

Update the _convert_numpy_types function to correctly handle numpy floating types by using a.item() for conversion to Float with appropriate precision, removing the faulty string conversion logic.

### I2 — Update _convert_numpy_types to use a.item()

Replace the string conversion logic with a direct conversion using a.item() to preserve the numeric value and set appropriate precision.

### I3 — Update _convert_numpy_types

Replace string conversion with a.item() for Float conversion.

```python
else:
    try:
        from sympy.core.numbers import Float
        prec = np.finfo(a).nmant + 1
        # Use the scalar value of the numpy float for conversion.
        return Float(a.item(), precision=prec)
    except NotImplementedError:
        raise SympifyError('Translation for numpy float : %s is not implemented' % a)
```

### I4 — Patch sympify.py

Patch sympy/core/sympify.py to fix numpy float conversion

## Rules

## References
