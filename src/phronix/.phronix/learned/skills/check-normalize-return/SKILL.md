---
name: check-normalize-return
description: Research on check normalize return. Covers how to identify which SymPy functions require dimensionless arguments; where and how should we check if function arguments are dimensionless; what dimension should functions with dimensionless args return. Approaches tried: class hierarchy check, explicit function list, follow pow pattern, prior incomplete fix.
subject: check-normalize-return
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to check normalize return |
| `R1` | Rules | Fix this in Apply the same validation pattern used by the Pow handler (l |
| `X1` | References | Tried: class-hierarchy-check |
| `X2` | References | Tried: explicit-function-list |
| `X3` | References | Tried: follow-pow-pattern |
| `X4` | References | Tried: prior-incomplete-fix |
| `X5` | References | Tried: return-dimensionless-for-transcendental |
| `X6` | References | Tried: normalize-single-arg-result |
| `X7` | References | Tried: check-all-args-then-normalize |
| `X8` | References | Tried: normalize-in-mul-handler |
| `X9` | References | Tried: no-tuple-unpacking-single-dim-return |
| `X10` | References | Sources consulted for check normalize return |
| `X11` | References | Tried: follow-pow-pattern-with-env-fix |
| `X12` | References | Tried: selective-normalization-via-class-check |
| `X13` | References | Tried: add-handler-semantic-equality |
| `X14` | References | Tried: incremental-tuple-then-validation |

















## Instructions

### I1 — How to evaluate a change to check normalize return

Figure of merit: **target_tests_passing** (max, target 1.0).

Measured by: Run the reproducer from issue.md: python3 -c "from sympy import exp; from sympy.physics import units; from sympy.physics.units.systems.si import SI; expr = units.second / (units.ohm * units.farad); buggy_expr = 100 + exp(expr); result = SI._collect_factor_and_dimension(buggy_expr); assert result[1] == SI.get_dimension_system().dim_dimensionless" - success rate (1.0 = pass, 0.0 = fail)

Cases differ along: arg_dimensionality, context, function_type.

## Rules

### R1 — Fix this in Apply the same validation pattern used by the Pow handler (l

Apply the same validation pattern used by the Pow handler (lines 170-172): check if dimension is_dimensionless, then set to 1. The Function handler should follow this exact pattern for transcendental functions.

Why it holds: The existing Pow handler correctly validates dimensionless requirements and provides the exact pattern to follow. Applying the same is_dimensionless() check and returning Dimension(1) for transcendental functions will fix the issue.

Confirmed on held-out instances (test 1/1, validate 1/1).

## References

### X1 — Tried: class-hierarchy-check

Check if function is ExpBase, TrigonometricFunction, HyperbolicFunction, or their inverse variants using isinstance(). If yes, verify args are dimensionless and return Dimension(1).

**Hypothesis**: SymPy's class hierarchy (ExpBase, TrigonometricFunction, etc.) fully captures all functions that require dimensionless arguments. A function is one of these types if and only if it requires dimensionless args.

**Status**: potential (train 1/1). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: explicit-function-list

Maintain a set of function class names that require dimensionless args. Check expr.func.__name__ against this set.

**Hypothesis**: An explicit whitelist of function names (exp, sin, cos, log, tan, etc.) is more maintainable and explicit than relying on class hierarchy, which might change.

**Status**: potential (train 1/1). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: follow-pow-pattern

Apply the same validation pattern used by the Pow handler (lines 170-172): check if dimension is_dimensionless, then set to 1. The Function handler should follow this exact pattern for transcendental functions.

**Hypothesis**: The existing Pow handler correctly validates dimensionless requirements and provides the exact pattern to follow. Applying the same is_dimensionless() check and returning Dimension(1) for transcendental functions will fix the issue.

**Status**: validated (validate 1/1). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: prior-incomplete-fix

Context approach: The prior fix for issue #20288 was incomplete. It fixed only a syntax error (tuple unpacking), not the semantic problem of validating that transcendental functions receive dimensionless arguments. This explains why the issue persists.

**Hypothesis**: The prior fix (commit b3d17030b8) addressed issue #20288 but only fixed a syntax error in the tuple unpacking, not the semantic issue of dimensional validation for transcendental functions. The Function handler still lacks dimensionless validation.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: return-dimensionless-for-transcendental

Transcendental functions (exp, sin, cos, log, etc.) with dimensionless arguments must return Dimension(1). This is mathematically required by power series definitions and confirmed by SymPy's test_issue_20288.

**Hypothesis**: Transcendental functions are defined via power series (e.g., exp(x) = 1 + x + x²/2! + ...) which can only sum terms with the same dimension. Therefore, the input must be dimensionless AND the output must be dimensionless (Dimension(1)). Falsifiable by: finding a transcendental function that can accept dimensional arguments or return dimensional results while maintaining mathematical consistency.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: normalize-single-arg-result

For single-argument functions: after collecting the argument's dimension, check if it's dimensionless using is_dimensionless(). If yes, return Dimension(1) explicitly. If no, return the argument's dimension as-is. For multi-arg functions, return dimensions[0].

**Hypothesis**: The bug occurs because Function handler returns un-normalized dimensionless dimensions (e.g., Dimension(time/(capacitance*impedance))) instead of the canonical Dimension(1). For single-arg transcendental functions, checking is_dimensionless() and normalizing will fix the issue. Falsified if: this breaks existing tests or if multi-arg functions need different handling.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: check-all-args-then-normalize

Collect all argument dimensions, check if ALL are dimensionless, then: if all dimensionless, return (rebuilt_function, Dimension(1)); otherwise return (rebuilt_function, dimensions[0]). This explicitly handles the single vs multi-arg case.

**Hypothesis**: When ALL arguments to a function are dimensionless, the result must be Dimension(1) (for transcendental functions this is mathematical requirement; for others it's safe default). Checking all args together and returning one dimension avoids tuple arity bugs. Falsified if: some non-transcendental functions need to propagate non-normalized dimensionless dimensions.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: normalize-in-mul-handler

Instead of fixing Function handler, fix the Mul handler (lines 156-166) to always normalize dimensionless results to Dimension(1) immediately after computing. This prevents un-normalized dimensionless dimensions from reaching the Function handler.

**Hypothesis**: The root cause is that Mul handler returns un-normalized dimensionless dimensions like Dimension(time/(capacitance*impedance)). If Mul normalizes these immediately (like Pow does), all downstream handlers get consistent Dimension(1). Falsified if: this breaks code that relies on preserving dimension structure even when dimensionless.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Tried: no-tuple-unpacking-single-dim-return

Modify Function handler to: (1) collect fds, (2) check len(fds)==1 (single-arg), (3) if yes and dimension is_dimensionless, return (factor, Dimension(1)), (4) else return (factor, dimensions[0]). For multi-arg, always return dimensions[0]. Never use tuple unpacking.

**Hypothesis**: Attempt 1 failed because it normalized each dimension in a list then unpacked with *(dims), which still creates tuple arity bugs. The correct fix is: collect dimensions, check if all are dimensionless, then return a SINGLE dimension (Dimension(1) if all dimensionless, else compute one dimension). Never unpack multiple dimensions. Falsified if: some code path requires returning >2 values from _coll

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X10 — Sources consulted for check normalize return

- 1. Wikipedia Dimensional Analysis article, section "Polynomials and transcendental functions" (https://en.wikipedia.org/wiki/Dimensional_analysis). 2. SymPy test_issue_20288 in sympy/physics/units/tes
- Git commit b3d17030b8, sympy/physics/units/tests/test_quantities.py line 531 (test_issue_20288), sympy/physics/units/unitsystem.py lines 192-196 (current code)
- Investigation shows second/(ohm*farad) has dimension Dimension(time/(capacitance*impedance)) which is_dimensionless==True but != Dimension(1). The Pow handler (lines 170-172) shows the normalization p

### X11 — Tried: follow-pow-pattern-with-env-fix

Apply the confirmed follow-pow-pattern approach from prior research: Check if ALL function args are dimensionless using is_dimensionless(), then return (rebuilt_function, Dimension(1)). Same code as skill I4.

**Hypothesis**: The follow-pow-pattern approach is confirmed from prior research and the implementation in skill I4 is correct. Attempt 2 failed due to pytest environment issue (verified by "No module named pytest" error), not code correctness. With pytest now available (verified), the same implementation will pass. Falsified if: regression tests fail even with pytest available.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X12 — Tried: selective-normalization-via-class-check

Check isinstance(expr, (ExpBase, TrigonometricFunction, HyperbolicFunction, InverseTrigonom  etricFunction, InverseHyperbolicFunction)) BEFORE normalizing to Dimension(1). For other functions, return first arg's dimension unchanged.

**Hypothesis**: The prior fix might have failed regression tests because it silently normalizes ALL functions, even ones that shouldn't require dimensionless args (like custom/user-defined functions). A defensive approach that ONLY normalizes known transcendental functions (exp, sin, cos, log, etc. via class hierarchy check) will preserve backward compatibility. Falsified if: no regression failures occur with uni

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X13 — Tried: add-handler-semantic-equality

Modify Add handler dimension comparison: instead of `if dim != addend_dim: raise`, check if BOTH are dimensionless using is_dimensionless(), allow the addition, and set result to Dimension(1). Only raise if truly incompatible.

**Hypothesis**: The root cause might not be the Function handler returning wrong dimensions, but the Add handler (lines 178-179) being too strict in dimension comparison. It uses dim != addend_dim (value equality) instead of checking semantic equivalence via is_dimensionless(). Making Add handler semantically aware would fix the issue without changing Function handler. Falsified if: Function handler actually IS t

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X14 — Tried: incremental-tuple-then-validation

Phase 1: Replace lines 195-196 with `return (expr.func(*(f[0] for f in fds)), fds[0][1])` - minimal change to fix tuple arity. Test regressions. Phase 2: Add dimensionless check and normalization only if Phase 1 passes.

**Hypothesis**: Attempt 2 may have failed because a single-stage fix introduced too much change at once (both fixing tuple unpacking AND adding dimensionless validation). A two-phase approach: (1) First fix only the tuple arity bug by returning dims[0] instead of *(dims), (2) Then verify that passes regressions, (3) Then add dimensionless validation. This isolates which part causes regression failures if any. Fal

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.
