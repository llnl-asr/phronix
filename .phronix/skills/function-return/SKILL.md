---
name: function-return
description: Research on function return. Covers how to identify which SymPy functions require dimensionless arguments; where and how should we check if function arguments are dimensionless; what dimension should functions with dimensionless args return. Approaches tried: class hierarchy check, explicit function list, follow pow pattern, prior incomplete fix.
subject: function-return
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to function return |
| `X1` | References | Tried: class-hierarchy-check |
| `X2` | References | Tried: explicit-function-list |
| `X3` | References | Tried: follow-pow-pattern |
| `X4` | References | Tried: prior-incomplete-fix |
| `X5` | References | Tried: return-dimensionless-for-transcendental |
| `X6` | References | Sources consulted for function return |








## Instructions

### I1 — How to evaluate a change to function return

Figure of merit: **target_tests_passing** (max, target 1.0).

Measured by: Run the reproducer from issue.md: python3 -c "from sympy import exp; from sympy.physics import units; from sympy.physics.units.systems.si import SI; expr = units.second / (units.ohm * units.farad); buggy_expr = 100 + exp(expr); result = SI._collect_factor_and_dimension(buggy_expr); assert result[1] == SI.get_dimension_system().dim_dimensionless" - success rate (1.0 = pass, 0.0 = fail)

Cases differ along: arg_dimensionality, context, function_type.

## Rules

## References

### X1 — Tried: class-hierarchy-check

Check if function is ExpBase, TrigonometricFunction, HyperbolicFunction, or their inverse variants using isinstance(). If yes, verify args are dimensionless and return Dimension(1).

**Hypothesis**: SymPy's class hierarchy (ExpBase, TrigonometricFunction, etc.) fully captures all functions that require dimensionless arguments. A function is one of these types if and only if it requires dimensionless args.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: explicit-function-list

Maintain a set of function class names that require dimensionless args. Check expr.func.__name__ against this set.

**Hypothesis**: An explicit whitelist of function names (exp, sin, cos, log, tan, etc.) is more maintainable and explicit than relying on class hierarchy, which might change.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: follow-pow-pattern

Apply the same validation pattern used by the Pow handler (lines 170-172): check if dimension is_dimensionless, then set to 1. The Function handler should follow this exact pattern for transcendental functions.

**Hypothesis**: The existing Pow handler correctly validates dimensionless requirements and provides the exact pattern to follow. Applying the same is_dimensionless() check and returning Dimension(1) for transcendental functions will fix the issue.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: prior-incomplete-fix

Context approach: The prior fix for issue #20288 was incomplete. It fixed only a syntax error (tuple unpacking), not the semantic problem of validating that transcendental functions receive dimensionless arguments. This explains why the issue persists.

**Hypothesis**: The prior fix (commit b3d17030b8) addressed issue #20288 but only fixed a syntax error in the tuple unpacking, not the semantic issue of dimensional validation for transcendental functions. The Function handler still lacks dimensionless validation.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: return-dimensionless-for-transcendental

Transcendental functions (exp, sin, cos, log, etc.) with dimensionless arguments must return Dimension(1). This is mathematically required by power series definitions and confirmed by SymPy's test_issue_20288.

**Hypothesis**: Transcendental functions are defined via power series (e.g., exp(x) = 1 + x + x²/2! + ...) which can only sum terms with the same dimension. Therefore, the input must be dimensionless AND the output must be dimensionless (Dimension(1)). Falsifiable by: finding a transcendental function that can accept dimensional arguments or return dimensional results while maintaining mathematical consistency.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Sources consulted for function return

- 1. Wikipedia Dimensional Analysis article, section "Polynomials and transcendental functions" (https://en.wikipedia.org/wiki/Dimensional_analysis). 2. SymPy test_issue_20288 in sympy/physics/units/tes
- Git commit b3d17030b8, sympy/physics/units/tests/test_quantities.py line 531 (test_issue_20288), sympy/physics/units/unitsystem.py lines 192-196 (current code)
