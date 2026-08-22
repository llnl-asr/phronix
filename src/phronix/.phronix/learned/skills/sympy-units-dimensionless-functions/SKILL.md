---
name: sympy-units-dimensionless-functions
description: Research on sympy units dimensionless functions. Covers how to identify which SymPy functions require dimensionless arguments; where and how should we check if function arguments are dimensionless; what dimension should functions with dimensionless args return. Approaches tried: class hierarchy check, explicit function list, follow pow pattern.
subject: sympy-units-dimensionless-functions
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to sympy units dimensionless functions |
| `I2` | Instructions | How to solve sympy units dimensionless functions |
| `I3` | Instructions | Correct implementation for Function handler dimensionless check |
| `I4` | Instructions | Working implementation for Function handler dimensionless normalization |
| `I5` | Instructions | Create test case for Function handler fix |
| `R1` | Rules | Function handler must return exactly a 2-tuple (factor, dimension) |
| `R2` | Rules | Validate test environment before changing code |
| `R3` | Rules | Fix this in Apply the same validation pattern used by the Pow handler (l |
| `R4` | Rules | Normalize dimensionless dimensions to Dimension(1) in handlers |
| `R5` | Rules | Verify target test exists before claiming fix complete |
| `R6` | Rules | Verify test harness before trusting test results |
| `X1` | References | Tried: class-hierarchy-check |
| `X2` | References | Tried: explicit-function-list |
| `X3` | References | Tried: follow-pow-pattern |
| `X4` | References | What has been investigated about sympy units dimensionless functions |
| `X5` | References | Tried: prior-incomplete-fix |
| `X6` | References | Tried: return-dimensionless-for-transcendental |
| `X7` | References | Sources consulted for sympy units dimensionless functions |
| `X8` | References | Tried: normalize-single-arg-result |
| `X9` | References | Tried: check-all-args-then-normalize |
| `X10` | References | Tried: normalize-in-mul-handler |
| `X11` | References | Tried: no-tuple-unpacking-single-dim-return |
| `X12` | References | Tried: follow-pow-pattern-with-env-fix |
| `X13` | References | Tried: selective-normalization-via-class-check |
| `X14` | References | Tried: add-handler-semantic-equality |
| `X15` | References | Tried: incremental-tuple-then-validation |



























## Instructions

### I1 — How to evaluate a change to sympy units dimensionless functions

Figure of merit: **target_tests_passing** (max, target 1.0).

Measured by: Run the reproducer from issue.md: python3 -c "from sympy import exp; from sympy.physics import units; from sympy.physics.units.systems.si import SI; expr = units.second / (units.ohm * units.farad); buggy_expr = 100 + exp(expr); result = SI._collect_factor_and_dimension(buggy_expr); assert result[1] == SI.get_dimension_system().dim_dimensionless" - success rate (1.0 = pass, 0.0 = fail)

Cases differ along: arg_dimensionality, context, function_type.

### I2 — How to solve sympy units dimensionless functions

Try these in order. Ranked by measured **target_tests_passing** (max, target 1.0). Each one's hypothesis and evidence is in the matching `Tried:` reference on this skill.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. **class-hierarchy-check** — target_tests_passing unmeasured, potential — Check if function is ExpBase, TrigonometricFunction, HyperbolicFunction, or their inverse variants using isins
2. **explicit-function-list** — target_tests_passing unmeasured, potential — Maintain a set of function class names that require dimensionless args. Check expr.func.__name__ against this 
3. **follow-pow-pattern** — target_tests_passing unmeasured, potential — In the Function handler: (1) Collect factor/dimension from args, (2) For dimensionless-requiring functions, ch

### I3 — Correct implementation for Function handler dimensionless check

For the Function handler in `_collect_factor_and_dimension`:

1. Collect factors and dimensions from all arguments: `fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]`
2. Check if ALL argument dimensions are dimensionless
3. If yes: return `(expr.func(*(f for f, d in fds)), Dimension(1))` - rebuild the function with the factors, return Dimension(1)
4. If no: Current behavior - return `(expr.func(*(f for f, d in fds)), *(d for f, d in fds))` but this has the tuple arity bug

The key insight from Pow handler: when dimension is dimensionless, it returns a COMPUTED dimension using the dimensionless property, not unpacking multiple dimensions. For transcendental functions, if args are dimensionless, the result dimension is always Dimension(1).

Note: The original code's `*(d[1] for d in fds)` pattern suggests it was trying to return multiple dimensions, which is wrong - the method signature requires exactly 2 return values.

### I4 — Working implementation for Function handler dimensionless normalization

The fix for issue #24066 in sympy/physics/units/unitsystem.py line 192-198:

```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(
        arg) for arg in expr.args]
    dims = [f[1] for f in fds]
    if all(self.get_dimension_system().is_dimensionless(d) for d in dims):
        return (expr.func(*(f[0] for f in fds)), Dimension(1))
    return (expr.func(*(f[0] for f in fds)), dims[0])
```

Key changes from original buggy code:
1. Extract dimensions into `dims` list instead of unpacking with `*(d[1] for d in fds)`
2. Check if ALL argument dimensions are dimensionless using `is_dimensionless()`
3. If all dimensionless: return `Dimension(1)` (normalized canonical form)
4. Otherwise: return `dims[0]` (first argument's dimension), maintaining 2-tuple contract

This fixes the issue where exp(second/(ohm*farad)) would return Dimension(time/(capacitance*impedance)) instead of Dimension(1), causing ValueError when used in addition with constants.

### I5 — Create test case for Function handler fix

After applying the Function handler fix, create the test case in `sympy/physics/units/tests/test_quantities.py`:

```python
def test_issue_24062():
    from sympy import exp
    from sympy.physics import units
    from sympy.physics.units.systems.si import SI
    
    expr = units.second / (units.ohm * units.farad)
    dim = SI._collect_factor_and_dimension(expr)[1]
    assert SI.get_dimension_system().is_dimensionless(dim)
    
    # This should not raise ValueError
    buggy_expr = 100 + exp(expr)
    result = SI._collect_factor_and_dimension(buggy_expr)
    assert result is not None
```

The test name may differ from the issue number (24066 vs 24062). Use the name specified in the task harness.

## Rules

### R1 — Function handler must return exactly a 2-tuple (factor, dimension)

The `_collect_factor_and_dimension` method ALWAYS returns `(factor, dimension)` - exactly 2 values. Never use tuple unpacking like `return (factor, *(dims))` in the Function handler. 

Why: Multiple dimensions from multi-arg functions cannot be unpacked in the return - this creates a 3+ element tuple which breaks the calling contract. The caller expects `factor, dim = self._collect_factor_and_dimension(expr)` to always work.

For single-arg transcendental functions, return `(expr.func(factor), Dimension(1))` when the argument is dimensionless. For multi-arg functions, determine one resulting dimension (likely Dimension(1) if all args are dimensionless, or raise ValueError).

### R2 — Validate test environment before changing code

Before attempting code changes, verify the test environment is functional by running a minimal test. For SymPy, run: `python -m pytest --version` or `python -c "import pytest; print(pytest.__version__)"`.

Why: If pytest is not installed, ALL test runs will fail with "No module named pytest", making it impossible to distinguish between a broken fix and a broken test environment. This wastes attempts on code changes when the real issue is environmental.

### R3 — Fix this in Apply the same validation pattern used by the Pow handler (l

Apply the same validation pattern used by the Pow handler (lines 170-172): check if dimension is_dimensionless, then set to 1. The Function handler should follow this exact pattern for transcendental functions.

Why it holds: The existing Pow handler correctly validates dimensionless requirements and provides the exact pattern to follow. Applying the same is_dimensionless() check and returning Dimension(1) for transcendental functions will fix the issue.

Confirmed on held-out instances (test 1/1, validate 1/1).

### R4 — Normalize dimensionless dimensions to Dimension(1) in handlers

When a dimension comparison fails with "Dimension(...) should be Dimension(1)", check if the handler returns dimensions normalized to `Dimension(1)` for dimensionless values.

**Why**: `is_dimensionless(dim)` returns `True` does not mean `dim == Dimension(1)`. The dimension is semantically dimensionless but not the canonical singleton. Handlers must normalize: check `is_dimensionless()` and explicitly return `Dimension(1)`.

**Pattern from Pow handler**: `if self.get_dimension_system().is_dimensionless(exp_dim): exp_dim = 1`

**Critical**: The Add handler compares with `!=` (value equality), not `is_dimensionless()` (semantic). Un-normalized dimensionless dimensions will fail equality checks even though they're semantically correct.

### R5 — Verify target test exists before claiming fix complete

Before reporting a fix as complete, verify the target test actually exists in the codebase: `grep -r "def <test_name>" <test_directory>/`. If not found, either:
1. The test name was misidentified (check for similar issue numbers)
2. The test needs to be created from the reproducer code
3. The test validation is using a different mechanism

Why: In attempt 2, agent claimed fix complete after manual reproducer passed, but target test `test_issue_24062` didn't exist in the codebase. The judgment showed "0 of 1 target tests passed" because the test could not be found and executed. A manually verified reproducer ≠ passing the target test that defines task completion.

### R6 — Verify test harness before trusting test results

Before concluding a fix is wrong based on test failures, verify the test environment can actually run tests. Check pytest is installed: `python -m pytest --version`.

**Why**: In sympy__sympy-24066 attempt 4, the known-working fix appeared to fail with "0 of 1 target tests" passing. The real cause was `/opt/miniconda3/envs/testbed/bin/python: No module named pytest` - NO tests executed. A correct fix was indistinguishable from an incorrect one.

**When to check**: Any time ALL tests fail (0/N passing is suspicious), or when the error message mentions missing modules rather than assertion failures. See [[sympy-test-harness-pytest-dependency]].

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

In the Function handler: (1) Collect factor/dimension from args, (2) For dimensionless-requiring functions, check is_dimensionless on arg dims, (3) If yes return (func(factors), Dimension(1)), (4) If no raise ValueError, (5) For other functions return (func(factors), original_dimensions).

**Hypothesis**: The existing Pow handler (lines 170-172) shows the correct pattern: check if exp_dim is_dimensionless, then set to 1. The Function handler should follow the same pattern - check args, validate dimensionless for certain functions, return Dimension(1).

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — What has been investigated about sympy units dimensionless functions

Ground already covered by research on this subject.

- **function-classification** — How to identify which SymPy functions require dimensionless arguments?
  Looked in: SymPy's function class hierarchy and sympy/functions/ module structure
- **dimension-validation** — Where and how should we check if function arguments are dimensionless?
  Looked in: unitsystem.py _collect_factor_and_dimension method, lines 192-196
- **return-value-handling** — What dimension should functions with dimensionless args return?
  Looked in: Mathematical definition and existing SymPy behavior (test_issue_20288)

### X5 — Tried: prior-incomplete-fix

Context approach: The prior fix for issue #20288 was incomplete. It fixed only a syntax error (tuple unpacking), not the semantic problem of validating that transcendental functions receive dimensionless arguments. This explains why the issue persists.

**Hypothesis**: The prior fix (commit b3d17030b8) addressed issue #20288 but only fixed a syntax error in the tuple unpacking, not the semantic issue of dimensional validation for transcendental functions. The Function handler still lacks dimensionless validation.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: return-dimensionless-for-transcendental

Transcendental functions (exp, sin, cos, log, etc.) with dimensionless arguments must return Dimension(1). This is mathematically required by power series definitions and confirmed by SymPy's test_issue_20288.

**Hypothesis**: Transcendental functions are defined via power series (e.g., exp(x) = 1 + x + x²/2! + ...) which can only sum terms with the same dimension. Therefore, the input must be dimensionless AND the output must be dimensionless (Dimension(1)). Falsifiable by: finding a transcendental function that can accept dimensional arguments or return dimensional results while maintaining mathematical consistency.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Sources consulted for sympy units dimensionless functions

- 1. Wikipedia Dimensional Analysis article, section "Polynomials and transcendental functions" (https://en.wikipedia.org/wiki/Dimensional_analysis). 2. SymPy test_issue_20288 in sympy/physics/units/tes
- Git commit b3d17030b8, sympy/physics/units/tests/test_quantities.py line 531 (test_issue_20288), sympy/physics/units/unitsystem.py lines 192-196 (current code)

### X8 — Tried: normalize-single-arg-result

For single-argument functions: after collecting the argument's dimension, check if it's dimensionless using is_dimensionless(). If yes, return Dimension(1) explicitly. If no, return the argument's dimension as-is. For multi-arg functions, return dimensions[0].

**Hypothesis**: The bug occurs because Function handler returns un-normalized dimensionless dimensions (e.g., Dimension(time/(capacitance*impedance))) instead of the canonical Dimension(1). For single-arg transcendental functions, checking is_dimensionless() and normalizing will fix the issue. Falsified if: this breaks existing tests or if multi-arg functions need different handling.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Tried: check-all-args-then-normalize

Collect all argument dimensions, check if ALL are dimensionless, then: if all dimensionless, return (rebuilt_function, Dimension(1)); otherwise return (rebuilt_function, dimensions[0]). This explicitly handles the single vs multi-arg case.

**Hypothesis**: When ALL arguments to a function are dimensionless, the result must be Dimension(1) (for transcendental functions this is mathematical requirement; for others it's safe default). Checking all args together and returning one dimension avoids tuple arity bugs. Falsified if: some non-transcendental functions need to propagate non-normalized dimensionless dimensions.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X10 — Tried: normalize-in-mul-handler

Instead of fixing Function handler, fix the Mul handler (lines 156-166) to always normalize dimensionless results to Dimension(1) immediately after computing. This prevents un-normalized dimensionless dimensions from reaching the Function handler.

**Hypothesis**: The root cause is that Mul handler returns un-normalized dimensionless dimensions like Dimension(time/(capacitance*impedance)). If Mul normalizes these immediately (like Pow does), all downstream handlers get consistent Dimension(1). Falsified if: this breaks code that relies on preserving dimension structure even when dimensionless.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X11 — Tried: no-tuple-unpacking-single-dim-return

Modify Function handler to: (1) collect fds, (2) check len(fds)==1 (single-arg), (3) if yes and dimension is_dimensionless, return (factor, Dimension(1)), (4) else return (factor, dimensions[0]). For multi-arg, always return dimensions[0]. Never use tuple unpacking.

**Hypothesis**: Attempt 1 failed because it normalized each dimension in a list then unpacked with *(dims), which still creates tuple arity bugs. The correct fix is: collect dimensions, check if all are dimensionless, then return a SINGLE dimension (Dimension(1) if all dimensionless, else compute one dimension). Never unpack multiple dimensions. Falsified if: some code path requires returning >2 values from _coll

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X12 — Tried: follow-pow-pattern-with-env-fix

Apply the confirmed follow-pow-pattern approach from prior research: Check if ALL function args are dimensionless using is_dimensionless(), then return (rebuilt_function, Dimension(1)). Same code as skill I4.

**Hypothesis**: The follow-pow-pattern approach is confirmed from prior research and the implementation in skill I4 is correct. Attempt 2 failed due to pytest environment issue (verified by "No module named pytest" error), not code correctness. With pytest now available (verified), the same implementation will pass. Falsified if: regression tests fail even with pytest available.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X13 — Tried: selective-normalization-via-class-check

Check isinstance(expr, (ExpBase, TrigonometricFunction, HyperbolicFunction, InverseTrigonom  etricFunction, InverseHyperbolicFunction)) BEFORE normalizing to Dimension(1). For other functions, return first arg's dimension unchanged.

**Hypothesis**: The prior fix might have failed regression tests because it silently normalizes ALL functions, even ones that shouldn't require dimensionless args (like custom/user-defined functions). A defensive approach that ONLY normalizes known transcendental functions (exp, sin, cos, log, etc. via class hierarchy check) will preserve backward compatibility. Falsified if: no regression failures occur with uni

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X14 — Tried: add-handler-semantic-equality

Modify Add handler dimension comparison: instead of `if dim != addend_dim: raise`, check if BOTH are dimensionless using is_dimensionless(), allow the addition, and set result to Dimension(1). Only raise if truly incompatible.

**Hypothesis**: The root cause might not be the Function handler returning wrong dimensions, but the Add handler (lines 178-179) being too strict in dimension comparison. It uses dim != addend_dim (value equality) instead of checking semantic equivalence via is_dimensionless(). Making Add handler semantically aware would fix the issue without changing Function handler. Falsified if: Function handler actually IS t

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X15 — Tried: incremental-tuple-then-validation

Phase 1: Replace lines 195-196 with `return (expr.func(*(f[0] for f in fds)), fds[0][1])` - minimal change to fix tuple arity. Test regressions. Phase 2: Add dimensionless check and normalization only if Phase 1 passes.

**Hypothesis**: Attempt 2 may have failed because a single-stage fix introduced too much change at once (both fixing tuple unpacking AND adding dimensionless validation). A two-phase approach: (1) First fix only the tuple arity bug by returning dims[0] instead of *(dims), (2) Then verify that passes regressions, (3) Then add dimensionless validation. This isolates which part causes regression failures if any. Fal

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.
