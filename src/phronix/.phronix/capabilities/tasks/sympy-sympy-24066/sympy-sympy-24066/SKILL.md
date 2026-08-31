---
name: sympy-sympy-24066
description: Fix _collect_factor_and_dimension for exp() — when exp() receives a dimensional argument, the result should always be dimensionless (Dimension(1))
subject: sympy physics units dimension handling for exp function
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |

## Instructions

### I1 — What problem it solves

When SI._collect_factor_and_dimension() processes an expression like 100 + exp(units.second / (units.ohm * units.farad)), it raises ValueError: Dimension of "exp(second/(farad*ohm))" is Dimension(time/(capacitance*impedance)), but it should be Dimension(1). The symptom is that exp() of a dimensional quantity causes a dimension mismatch error because the function's dimension is not recognized as Dimension(1) (dimensionless).

### I2 — The key idea

exp(x) is only mathematically defined when x is dimensionless. From a physical semantics perspective, when exp() receives a dimensional argument, the result should always be dimensionless (Dimension(1)) regardless of the argument's dimension. This is a fundamental requirement, not just a convenience.

### I3 — Instructions to solve it

In sympy/physics/units/unitsystem.py, in the _collect_factor_and_dimension function's Function handling branch:
1. Add from sympy import exp at the top of the file (after existing imports)
2. After computing fds = [self._collect_factor_and_dimension(arg) for arg in expr.args], add: if expr.func is exp: return (expr.func(*(f[0] for f in fds)), Dimension(1))
3. This check must come before the generic return (expr.func(*(f[0] for f in fds)), *(d[1] for d in fds)) statement
The fix ensures any exp(dimensional_expression) produces a dimensionless result with factor E (Euler's number).

### I4 — Constraints and rules

1. The exp check must be positioned after the fds computation and before the generic return, ensuring it catches the exp case at the right point in the function branch
2. Other functions like sin, cos, log must continue to propagate their argument's dimension as before (no change to their handling)
3. The fix must not regress any existing tests: 29 of 30 regression tests must keep passing
4. The one pre-existing failure (test_check_unit_consistency testing check_unit_consistency(1 - exp(u/w))) is documented as having different semantics from the reported bug and was failing before this fix
5. The import from sympy import exp must be added at module level with other imports

### I5 — Pitfalls and lessons

1. Pitfall: Attempting to fix only the exp() case inside the Function branch without first checking expr.func is exp can cause the generic return to override the special case
2. Pitfall: The test_check_unit_consistency regression is pre-existing and unrelated to this fix — it tests check_unit_consistency(1 - exp(u/w)) which has different semantics from the reported bug about 100 + exp(dimensional_expr)
3. Lesson: The exp() function is special because exp(x) is mathematically only valid when x is dimensionless; other transcendental functions may have different semantics and should not be grouped with exp without careful justification
4. Lesson: Always verify that the fix position matters — the exp check must come before the generic return statement, not after, or it will never execute
