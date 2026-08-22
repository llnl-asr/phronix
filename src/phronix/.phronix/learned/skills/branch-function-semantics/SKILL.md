---
name: branch-function-semantics
description: Research on branch function semantics. Covers in _collect_factor_and_dimension's `elif isinstance(expr, Function)` branch (sympy/physics/units/unitsystem.py ~192-196), what is the correct dimension to return for expr.func(*args)? Should it check that every arg dimension is_dimensionless (like the Pow branch does at line 170) and return Dimension(1) for the whole Function result, rather than passing through each arg's raw dimension; for a Function with multiple arguments (e.g. atan2(y, x)), should _collect_factor_and_dimension require all arguments to individually be dimensionless (mirroring ho
subject: branch-function-semantics
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to branch function semantics |
| `I2` | Instructions | How to solve branch function semantics |
| `I3` | Instructions | Fallback approaches for branch function semantics |
| `I4` | Instructions | Steps to solve branch function semantics |
| `X1` | References | Tried: fix-function-branch-dimensionless-check |
| `X2` | References | Tried: function-branch-return-dimension1-no-raise |
| `X3` | References | Sources consulted for branch function semantics |
| `X4` | References | What has been investigated about branch function semantics |
| `X5` | References | Where research on this subject stands |


















## Instructions

### I1 — How to evaluate a change to branch function semantics

Figure of merit: **collect_factor_and_dimension_correctness_rate** (max, target 1.0).

Measured by: Fraction of corpus instances for which SI._collect_factor_and_dimension(expr) (a) does not raise ValueError when the expression is dimensionally consistent (e.g. functions like exp/sin/log/cos applied to a dimensionless argument, and Add/Mul/Pow combinations built from such), (b) DOES raise ValueError when the expression is genuinely dimensionally inconsistent (e.g. exp() applied to a non-dimensio

Cases differ along: arg_dimensionality, context, expected_outcome, function_type.

### I2 — How to solve branch function semantics

Try these in order, ONE at a time. Ranked by measured **collect_factor_and_dimension_correctness_rate** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A1` **fix-function-branch-dimensionless-check** — collect_factor_and_dimension_correctness_rate unmeasured, potential — In sympy/physics/units/unitsystem.py, rewrite the Function branch of _collect_factor_and_d
2. `A2` **function-branch-return-dimension1-no-raise** — collect_factor_and_dimension_correctness_rate unmeasured, potential — In sympy/physics/units/unitsystem.py, change the Function branch to `fds = [self._collect_

### I3 — Fallback approaches for branch function semantics

If the leading approach fails, these were also measured, ranked by the same metric.

**`A2` function-branch-return-dimension1-no-raise** — collect_factor_and_dimension_correctness_rate unmeasured
  1. Locate Function branch (judgement)
  2. Replace return with simple Dimension(1) default (judgement)
  3. Reproduce issue script (judgement)
  4. Run existing unit system tests (judgement)## Rules

### I4 — Steps to solve branch function semantics

The steps that solve branch function semantics, in order. Run them.

1. `locate_unitsystem_function_branch(...)` — Locate _collect_factor_and_dimension Function branch
2. `probe_reproduce_dimension_issue(...)` — Reproduce the reported bug
3. **Rewrite branch to validate and normalize dimension** (judgement — no tool for this)
   Replace the malformed tuple-returning Function branch with logic that: for each arg, computes (factor, dim) via recursive _collect_factor_and_dimension; raises ValueError (matching the Add branch's me
4. `probe_reproduce_dimension_issue(...)` — Verify reproduction now succeeds
5. `probe_run_pytest_selection(...)` — Run existing unit system regression tests

## References

### X1 — Tried: fix-function-branch-dimensionless-check

In sympy/physics/units/unitsystem.py, rewrite the Function branch of _collect_factor_and_dimension: for each arg, get (factor, dim); if dim is not dimensionless (via self.get_dimension_system().is_dimensionless(dim)), raise ValueError like the Add branch does; otherwise treat it as scalar. Return (e

**Hypothesis**: The `elif isinstance(expr, Function)` branch in _collect_factor_and_dimension (sympy/physics/units/unitsystem.py:192-196) is structurally wrong: it returns a tuple of (value, *all_arg_dims) instead of (value, dimension), and never checks/normalizes that transcendental function arguments (exp, sin, etc.) are dimensionless. This is why `exp(second/(farad*ohm))`, whose argument dim is dimensionless p

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: function-branch-return-dimension1-no-raise

In sympy/physics/units/unitsystem.py, change the Function branch to `fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]; return expr.func(*(f[0] for f in fds)), Dimension(1)` — no dimensionless validation, just fixing the malformed return tuple and defaulting to Dimension(1) like t

**Hypothesis**: Instead of raising ValueError for non-dimensionless function args (approach A1), simply always return Dimension(1) for any Function node's dimension, without validating each arg — mirroring how the else-branch already defaults unknown exprs to Dimension(1). This is simpler and avoids risk of new ValueErrors breaking currently-passing calls where a Function is applied to a non-strictly-dimensionles

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Sources consulted for branch function semantics

- issue.md reproduction + sympy/physics/units/unitsystem.py:192-196 (read directly)

### X4 — What has been investigated about branch function semantics

Ground already covered by research on this subject.

- **function_branch_semantics** — In _collect_factor_and_dimension's `elif isinstance(expr, Function)` branch (sympy/physics/units/unitsystem.py ~192-196), what is the correct dimension to return for expr.func(*args)? Should it check 
  Looked in: sympy/physics/units/unitsystem.py, the Function elif branch and its interaction with is_dimensionless
- **multi_arg_function_dimension_semantics** — For a Function with multiple arguments (e.g. atan2(y, x)), should _collect_factor_and_dimension require all arguments to individually be dimensionless (mirroring how transcendental single-arg function
  Looked in: sympy/physics/units/*.py — search for other Function-dimension special cases, and existing tests in sympy/physics/units/tests/ that exercise Function nodes
- **existing_test_coverage_and_regressions** — What do the existing tests in sympy/physics/units/tests/test_quantities.py (and any test_unitsystem.py) already assert about _collect_factor_and_dimension with Function nodes (exp, sqrt, log, Abs, etc
  Looked in: sympy/physics/units/tests/test_quantities.py, git blame/log around unitsystem.py for prior related fixes

### X5 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **collect_factor_and_dimension_correctness_rate** (max, target 1.0).

**Established**
- fix-function-branch-dimensionless-check (working)

**Still open**
- function-branch-return-dimension1-no-raise (potential)
- sympy/physics/units/unitsystem.py (potential collect_factor_and_dimension_correctness_rate=1.0)
- aspect not yet answered: function_branch_semantics
- aspect not yet answered: multi_arg_function_dimension_semantics
- aspect not yet answered: existing_test_coverage_and_regressions

**Where the detail is**
- fix-function-branch-dimensionless-check: issue.md reproduction + sympy/physics/units/unitsystem.py:192-196 (read directly)
- function-branch-return-dimension1-no-raise: unitsystem.py:192-200, contrasted with A1
- sympy/physics/units/unitsystem.py: benchmark attempt
- full record: research topic `sympy__sympy-24066` (via research_status, only if this summary is not enough)