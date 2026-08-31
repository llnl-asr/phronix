---
name: sympy-sympy-13146
description: The sympy-mathematica-printer-fix subject.
subject: sympy-sympy-13146
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Resolve email field name mismatch |
| `I2` | Instructions | Add alias to custom user model |
| `I3` | Instructions | Normalize float exponents in Power.__new__ |
| `I4` | Instructions | Update imports for collections |
| `R1` | Rules | Maintain existing test suite |
| `R2` | Rules | Do not alter public API semantics |
| `R3` | Rules | _print_Float formatting fix |

## Instructions

### I1 — Resolve email field name mismatch

In the code that accesses the email attribute, replace direct `user.email` with `getattr(user, get_email_field_name(), "")` where `get_email_field_name()` returns the correct attribute name (e.g., `email_address`).

### I2 — Add alias to custom user model

In the custom user model definition, add a property `email` that returns `self.email_address` to provide backward compatibility.

### I3 — Normalize float exponents in Power.__new__

In `sympy/core/power.py` inside `Power.__new__`, after sympifying the exponent `e`, add:
```
if e.is_Float:
    try:
        e = Rational(str(e))
    except Exception:
        pass
```

### I4 — Update imports for collections

Replace deprecated `from collections import Mapping, Callable` with `from collections.abc import Mapping, Callable` in affected modules.

## Rules

### R1 — Maintain existing test suite

All existing regression tests (34) must continue to pass after changes.

### R2 — Do not alter public API semantics

The `email` alias must behave identically to the original `email_address` field without introducing side effects.

### R3 — _print_Float formatting fix

Fix _print_Float to use '{:g}' format which strips trailing zeros and uses 'e' for scientific notation, then replace 'e' with Mathematica *^ notation.
Original '{:.15g}' format produced trailing zeros (e.g., '3.50000000000000') and the 'e' replacement didn't activate for numbers like 3.5 that don't use e-notation.

## References
