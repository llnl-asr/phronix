---
name: sympy-sympy-21379
description: Fix PolynomialError when calling expr.subs({1: 1.0}) on expressions with Piecewise generators and hyperbolic functions. The issue occurred in _eval_is_real methods of sinh, cosh, and tanh when im contains a Piecewise expression and im % pi is computed, triggering a gcd → parallel_poly_from_expr chain that raises PolynomialError.
subject: sympy-sympy-21379
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem and Fix Overview |
| `I2` | Instructions | What problem it solves |
| `I3` | Instructions | The key idea |

## Instructions

### I1 — Problem and Fix Overview

**Problem**: Unexpected `PolynomialError` when calling `subs({1: 1.0})` on expressions containing a `Piecewise` inside hyperbolic functions with real‑valued symbols.

**Key Idea**: Guard against evaluating the real‑assumption path for `Piecewise` in hyperbolic functions by returning `None` in `_eval_is_real`.

**Instructions**:
1. Open `sympy/functions/elementary/hyperbolic.py`.
2. Locate the `_eval_is_real` method in the hyperbolic class (`sinh`, `cosh`, `tanh`).
3. After the `if arg.is_real:` block, add:
```python
if arg.func is Piecewise:
    return None  # defer to default handling
```
4. Ensure the method now returns `None` for `Piecewise` arguments, preventing the modulo‑pi polynomial conversion that raises `PolynomialError`.

### I2 — What problem it solves

PolynomialError: Piecewise generators do not make sense when calling expr.subs({1: 1.0}) on expressions like exp(sinh(Piecewise((x, y > x), (y, True)) / z)) with real symbols, triggered through _eval_is_real → im % pi → Mod → gcd chain.

### I3 — The key idea

the imaginary part `im` may contain a Piecewise expression and must be checked with `.is_number` before computing `im % pi`

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **sympy-sympy-21379-fom** (max, target 1.0).

**Established**
- A1 (working)

**Still open**
- sympy/functions/elementary/hyperbolic.py (potential)

**Where the detail is**
- sympy/functions/elementary/hyperbolic.py: benchmark attempt
- A1: code inspection of hyperbolic.py lines 243-253, 431-444, 657-672
- full record: research topic `sympy__sympy-21379` (via research_status, only if this summary is not enough)
