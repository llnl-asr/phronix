---
name: function
description: Research on function. Covers in unitsystem.py's _collect_factor_and_dimension, the elif isinstance(expr, Function) branch (lines 192-196) returns expr.func(*(f[0] for f in fds)), *(d[1] for d in fds) -- i.e. it passes through each argument's dimension unmodified and unpacks them into the return tuple instead of validating that args are dimensionless and returning a single Dimension(1). Confirm this is the exact defect (not e.g. a get_dimensional_expr issue) and what the correct replacement logic should be, referencing how get_dimensional_expr's own Function branch (lines 143-147) already check
subject: function
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to function |
| `I2` | Instructions | How to solve function |
| `X1` | References | Where research on this subject stands |
| `X3` | References | Tried: normalize-per-arg-dimensionless |
| `X4` | References | Tried: require-all-args-dimensionless-like-get_dimensional_expr |
| `X5` | References | Tried: fix-general-multiarg-return-arity-bug |
| `X6` | References | Tried: plain-valueerror-mirrored-template |
| `X7` | References | Tried: custom-exception-subclass |
| `X8` | References | Tried: function-branch-fix-with-multiarg-dimension-check |
| `X9` | References | Tried: fix_collect_factor_and_dimension_function_branch |
| `X10` | References | Tried: check-dimensionless-in-derivative-and-pow-too |
| `X11` | References | Tried: apply-normalize-per-arg-with-verified-test-runner |
| `X12` | References | Tried: extend-normalization-to-derivative-branch |
| `X13` | References | Sources consulted for function |


































































































































































































































































## Instructions

### I1 — How to evaluate a change to function

Figure of merit: **fraction_of_instances_with_correct_factor_and_dimension** (max, target 1.0).

Measured by: For each corpus instance, call SI._collect_factor_and_dimension(expr) (or Quantity._collect_factor_and_dimension for legacy-API cases) inside a fresh python -c invocation of the repo checkout, and compare the returned (factor, dimension) pair against the expected pair, or confirm a ValueError is raised for genuinely dimensionally-inconsistent expressions. Score = (# instances matching expected beh

Cases differ along: arg_dimensionality, context, function_arity, function_kind.

### I2 — How to solve function

Try these in order, ONE at a time. Ranked by measured **fraction_of_instances_with_correct_factor_and_dimension** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A4` **normalize-per-arg-dimensionless** — fraction_of_instances_with_correct_factor_and_dimension unmeasured, potential — In _collect_factor_and_dimension's Function branch (unitsystem.py), build dims via `Dimens
2. `A5` **require-all-args-dimensionless-like-get_dimensional_expr** — fraction_of_instances_with_correct_factor_and_dimension unmeasured, potential — Mirror get_dimensional_expr's Function branch semantics (`if all(i == 1 for i in args): re
3. `A6` **fix-general-multiarg-return-arity-bug** — fraction_of_instances_with_correct_factor_and_dimension unmeasured, potential — Also fix the general bug that _collect_factor_and_dimension's Function branch returns (fac

...and 11 lower-ranked approach(es); see `research_rank`.## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **fraction_of_instances_with_correct_factor_and_dimension** (max, target 1.0).

**Established**
- require-all-args-dimensionless-like-get_dimensional_expr (potential)
- fix-general-multiarg-return-arity-bug (potential)
- custom-exception-subclass (potential)

**Still open**
- plain-valueerror-mirrored-template (potential)
- function-branch-fix-with-multiarg-dimension-check (potential)
- sympy/physics/units/unitsystem.py (potential fraction_of_instances_with_correct_factor_and_dimension=0.0)
- fix_collect_factor_and_dimension_function_branch (potential)
- check-dimensionless-in-derivative-and-pow-too (potential)
- apply-normalize-per-arg-with-verified-test-runner (potential)

**Ruled out**
- get_dimensional_expr_is_root_cause (failed) — try 1: target tests still failing: test_issue_24062
- add_branch_is_root_cause (failed) — try 2: target tests still failing: test_issue_24062
- normalize-per-arg-dimensionless (failed) — try 3: target tests still failing: test_issue_24062

**Where the detail is**
- get_dimensional_expr_is_root_cause: Code reading of unitsystem.py:143-147 and 192-196; confirmed no call from _collect_factor_and_dimension to get

...and 6 more line(s); see the full record.### X2 — What has been investigated about function

Ground already covered by research on this subject.

- **function_branch_root_cause** — In unitsystem.py's _collect_factor_and_dimension, the elif isinstance(expr, Function) branch (lines 192-196) returns expr.func(*(f[0] for f in fds)), *(d[1] for d in fds) -- i.e. it passes through eac
  Looked in: sympy/physics/units/unitsystem.py lines 143-150 (get_dimensional_expr Function branch) and 192-196 (_collect_factor_and_dimension Function branch)
- **multiarg_function_semantics** — For a Function with more than one argument (e.g. atan2, Max), what should _collect_factor_and_dimension return when each argument's dimension is separately checked? Does every arg need to be dimension
  Looked in: sympy/physics/units/tests/test_quantities.py existing Function-related assertions; sympy/functions definitions of is_dimensionless-relevant assumptions
- **error_reporting_expectations** — When a Function argument IS dimensioned and non-dimensionless (e.g. sin(second)), what error should _collect_factor_and_dimension raise -- should it mirror the ValueError message format used elsewhere
  Looked in: sympy/physics/units/unitsystem.py Add branch error format (lines 178-182); sympy/physics/units/tests/test_quantities.py existing raises(ValueError) blocks near

### X3 — Tried: normalize-per-arg-dimensionless

In _collect_factor_and_dimension's Function branch (unitsystem.py), build dims via `Dimension(1) if is_dimensionless(d[1]) else d[1] for d in fds`, then return (expr.func(*factors), *dims). Matches actual upstream PR #24066 diff exactly. Adds test_issue_24062 to test_quantities.py using exp() (singl

**Hypothesis**: The bug is that dimensionless-but-not-literally-Dimension(1) sub-expression dimensions (e.g. impedance*capacitance/time canceling to dimensionless) fail equality checks later (e.g. in Add branch) because they aren't normalized to the canonical Dimension(1) object. Normalizing per-argument fixes this without touching return arity. Verified true by matching the actual merged upstream diff.

**Status**: potential (train 1/1). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: require-all-args-dimensionless-like-get_dimensional_expr

Mirror get_dimensional_expr's Function branch semantics (`if all(i == 1 for i in args): return S.One`, else rebuild expr.func(*args) symbolically) into _collect_factor_and_dimension, i.e. require ALL args dimensionless before collapsing.

**Hypothesis**: REFUTED. get_dimensional_expr and _collect_factor_and_dimension are different methods (one returns a dimension expression, the other a (factor, dimension) pair) and the actual upstream fix does not unify their semantics. Mirroring the all-args-dimensionless collapse into _collect_factor_and_dimension is not what the accepted PR does and would be a mismatched/over-scoped design.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: fix-general-multiarg-return-arity-bug

Also fix the general bug that _collect_factor_and_dimension's Function branch returns (factor, *dims) with len 1+N for an N-arg Function, instead of a strict 2-tuple like every other branch (Mul, Pow, Add, Derivative, Quantity, Dimension, else) — which breaks `factor, dim = ...` unpacking for multi-

**Hypothesis**: REFUTED as in-scope for this task. This is a real residual bug, but it is NOT fixed by PR #24066 — it is fixed later by a separate PR #30016 ("Fix _collect_factor_and_dimension returning variable-length tuple for Functions"). Implementing this broader fix for issue/PR 24066 would be over-scoping beyond what the accepted upstream fix actually changed.

**Status**: potential (train 0/1). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: plain-valueerror-mirrored-template

Fix Function branch of _collect_factor_and_dimension to check each arg's dimension is dimensionless, raising plain ValueError with the same template used by the existing Add branch: 'Dimension of "{}" is {}, but it should be {}'.format(arg, arg_dim, Dimension(1)). No custom exception subclass exists

**Hypothesis**: The established idiom in this method is plain ValueError with a .format()-built message naming the offending sub-expression, its actual dimension, and its expected dimension (see Add branch at unitsystem.py ~178-182). Mirroring this exact template for the Function branch keeps error reporting consistent across the method. Would be falsified if maintainers/tests expect a different exception type or

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: custom-exception-subclass

Considered whether a custom exception subclass (specific to units/dimension errors) should be raised instead of plain ValueError.

**Hypothesis**: A dedicated exception class might exist or be expected for dimensional-consistency errors in sympy.physics.units.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: function-branch-fix-with-multiarg-dimension-check

Same edit site as A1 (unitsystem.py Function branch, lines 192-196), but explicitly validate EACH argument's dimension individually rather than just checking the aggregate is_dimensionless once — for multi-arg functions (e.g. atan2(y, x), Max, Min) each argument must independently be dimensionless (

**Hypothesis**: If per-argument dimensionless validation happens inside the loop (raising as soon as a non-dimensionless arg is found) rather than after building the full fds list, error messages for cases like exp(units.meter) name the specific bad argument instead of a generic mismatch. Falsifiable: construct a multi-arg case, e.g. atan2(units.second, 1), and check whether the raised ValueError text identifies 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Tried: fix_collect_factor_and_dimension_function_branch

In sympy/physics/units/unitsystem.py, Function branch of _collect_factor_and_dimension (~lines 192-196): for each arg's (factor, dim), require self.get_dimension_system().is_dimensionless(dim); raise ValueError with the Add-branch-style message for the first offending arg, else return (expr.func(*(f

**Hypothesis**: Confirmed by direct code read (not just prior speculation): current code at unitsystem.py:192-196 returns (factor, *dims) via splat, which for exp(second/(farad*ohm)) leaks the raw non-Dimension(1) dimension instead of recognizing it as dimensionless. Replacing with an is_dimensionless check + Dimension(1) return fixes the issue's reproduction case. Falsified if applying this change still raises/f

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X10 — Tried: check-dimensionless-in-derivative-and-pow-too

Broaden the same is_dimensionless fix beyond the Function branch: also audit the Derivative branch (unitsystem.py ~185-191) and confirm Pow's exponent handling (~167-172, already does is_dimensionless) so all three branches use one shared helper `_dimensionless_or_raise(dim, context_expr)` instead o

**Hypothesis**: If the issue's target test suite includes cases beyond plain exp() (e.g. Derivative of a dimensionless-canceling expression, or nested Function calls), a Function-only patch could leave some target instances failing. Falsified if the target test (test_issue_24062) only exercises the exp() case and passes with the narrower Function-only fix, making this broader refactor unnecessary.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X11 — Tried: apply-normalize-per-arg-with-verified-test-runner

Implement A4 (normalize-per-arg-dimensionless) exactly: in unitsystem.py's Function branch (~line 192-196), change `return (expr.func(*(f[0] for f in fds)), *(d[1] for d in fds))` to first map each fds dimension through `Dimension(1) if self.get_dimension_system().is_dimensionless(d[1]) else d[1]`, 

**Hypothesis**: The A4 fix is correct (matches merged upstream PR #24066 diff exactly) and the prior attempt's failure was purely an environment/harness gap (missing pytest), not a defect in the logic. This is falsified if, after applying the exact edit and running the issue.md repro plus existing units tests with a confirmed-working runner, test_issue_24062-equivalent behavior still raises ValueError or any exis

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X12 — Tried: extend-normalization-to-derivative-branch

If A4 alone leaves a residual failure for expressions combining Derivative and Function (e.g. exp() wrapping a derivative of a dimensionless ratio), also apply the same is_dimensionless-normalization step to the Derivative branch (unitsystem.py ~lines 185-190), which currently divides dim by idim**c

**Hypothesis**: Believe: if the target test's expression nests a Derivative inside a Function argument, the Function branch fix alone (A4) is insufficient because the leaked non-canonical dimension originates one level deeper, in the Derivative branch, before ever reaching Function's fds list. Falsified if the issue's repro case (exp(second/(ohm*farad)), no Derivative involved) is representative of the target tes

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X13 — Sources consulted for function

- Direct code reading of unitsystem.py Function branch; considering multi-arg Function subclasses (atan2, Max, Min) that the single-arg-only reproduction case in the issue does not exercise.
- Direct comparison of get_dimensional_expr (unitsystem.py lines 130-150) against actual upstream PR #24066 diff, which touches only _collect_factor_and_dimension and the test file, not get_dimensional_
- Direct read of this attempt's checkout sympy/physics/units/unitsystem.py:130-200 (HEAD 98f86c2d16); issue.md repro; prior attempt's environment failure (No module named pytest) means the idea was neve
- GitHub issue/PR search confirming PR #30016 exists as the later, separate fix for this exact residual arity bug.
- Upstream PR #24066 diff (tmp/research/pr24066.diff from prior session); attempt-2/attempt-notes.md showing prior failure was 'No module named pytest', not a logic failure
- Upstream PR #24066 diff fetched via curl from patch-diff.githubusercontent.com/raw/sympy/sympy/pull/24066.diff, saved at tmp/research/pr24066.diff
