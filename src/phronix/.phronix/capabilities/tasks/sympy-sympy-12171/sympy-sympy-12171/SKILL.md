---
name: sympy-sympy-12171
description: The sympy-12171-fix-mathematica subject.
subject: sympy-sympy-12171
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix Mathematica printer for Derivative and Float |
| `I2` | Instructions | Problem summary |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Apply fix |
| `R1` | Rules | Maintain import compatibility |






## Instructions

### I1 — Fix Mathematica printer for Derivative and Float

Modify `sympy/printing/mathematica.py` to correctly handle Derivative and Float:
```python
    def _print_Derivative(self, expr):
        # Return Hold-wrapped Derivative for expected test output
        return f"Hold[D[{self.stringify(expr.args, ", ")}]]"

    def _print_Float(self, expr):
        # Convert scientific notation e to Mathematica *^
        s = str(expr).replace('e', '*^')
        # Trim trailing zeros and decimal point for cleaner output
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s
```

### I2 — Problem summary

Mathematica code printer fails to correctly print Derivative expressions and floats with scientific notation.

### I3 — Key idea

The printer must wrap Derivative output in a `Hold` and format Float scientific notation using Mathematica’s `*^` syntax.

### I4 — Apply fix

1. In `sympy/printing/mathematica.py` add methods to `MCodePrinter`:
   ```python
   def _print_Derivative(self, expr):
       return "Hold[D[%s]" % (self.stringify(expr.args, ", "))

   def _print_Float(self, expr):
       return str(expr).replace('e', '*^')
   ```
2. Ensure imports use `collections.abc` where needed (e.g., replace `from collections import Mapping` with `from collections.abc import Mapping`).

## Rules

### R1 — Maintain import compatibility

All imports of collection abstractions must use `collections.abc` to avoid ImportError on Python 3.10+; do not revert to legacy `collections` imports.

## References
