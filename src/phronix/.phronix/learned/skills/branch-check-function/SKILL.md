---
name: branch-check-function
description: Research on branch check function. Covers in _collect_factor_and_dimension's `elif isinstance(expr, Function)` branch (unitsystem.py ~192-196), how should the returned dimension be computed so that when an argument's dimension is dimensionless (per get_dimension_system().is_dimensionless), the Function's overall dimension collapses to Dimension(1) instead of passing through the argument's raw (non-trivial-but-dimensionless) Dimension object, which later fails `dim != addend_dim` equality checks in Add; for multi-argument Functions (e.g. atan2), the current code returns `(expr.func(*(f[0] for f
subject: branch-check-function
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to branch check function |
| `I2` | Instructions | How to solve branch check function |
| `I3` | Instructions | Fallback approaches for branch check function |
| `I4` | Instructions | Steps to solve branch check function |
| `X1` | References | Tried: function-arg-dimensionless-check |
| `X2` | References | Tried: add-branch-equivalence-check |
| `X3` | References | Sources consulted for branch check function |
| `X4` | References | What has been investigated about branch check function |
| `X5` | References | Where research on this subject stands |




















## Instructions

### I1 — How to evaluate a change to branch check function

Figure of merit: **fraction_of_collect_factor_dimension_cases_correct** (max, target 1.0).

Measured by: For each corpus instance, call SI._collect_factor_and_dimension(expr) (or the relevant UnitSystem instance) and check: (a) no exception is raised when the expected behaviour is success, (b) the returned Dimension for a dimensionless argument to a transcendental Function (exp, log, sin, cos, etc.) is exactly Dimension(1) (equivalently get_dimension_system().is_dimensionless(dim) is True and dim == 

Cases differ along: arg_dimensionality, expected_outcome, function_type, multi_arg_function, nesting.

### I2 — How to solve branch check function

Try these in order, ONE at a time. Ranked by measured **fraction_of_collect_factor_dimension_cases_correct** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A1` **function-arg-dimensionless-check** — fraction_of_collect_factor_dimension_cases_correct unmeasured, potential — In UnitSystem._collect_factor_and_dimension (sympy/physics/units/unitsystem.py, Function b
2. `A2` **add-branch-equivalence-check** — fraction_of_collect_factor_dimension_cases_correct unmeasured, potential — Alternative layer: instead of touching the Function branch, change the Add branch in _coll

### I3 — Fallback approaches for branch check function

If the leading approach fails, these were also measured, ranked by the same metric.

**`A2` add-branch-equivalence-check** — fraction_of_collect_factor_dimension_cases_correct unmeasured
  1. Reproduce the failure (judgement)
  2. Read the Add branch (judgement)
  3. Replace strict inequality with dimension-system equivalence  (judgement)
  4. Re-run the reproduction snippet (judgement)
  5. Run existing units test suite and check mismatch-detection t (judgement)## Rules

### I4 — Steps to solve branch check function

The steps that solve branch check function, in order. Run them.

1. `probe_reproduce_dimension_issue(...)` — Reproduce the failure
2. `probe_read_file_region(...)` — Read the Function branch
3. **Patch the branch to collapse dimensionless args** (judgement — no tool for this)
   Modify the branch so that for each (factor, dim) pair collected from expr.args, if self.get_dimension_system().is_dimensionless(dim) is True, the dimension contributed to the result is Dimension(1) in
4. `probe_reproduce_dimension_issue(...)` — Re-run the reproduction snippet
5. `probe_run_pytest_selection(...)` — Run existing units test suite

## References

### X1 — Tried: function-arg-dimensionless-check

In UnitSystem._collect_factor_and_dimension (sympy/physics/units/unitsystem.py, Function branch ~line 192-196), when handling a generic Function like exp/log, check whether each argument's collected dimension is dimensionless via self.get_dimension_system().is_dimensionless(d); if so, treat that arg

**Hypothesis**: The root cause is that the Function branch never calls is_dimensionless on argument dimensions before propagating them as the function's output dimension. If true, patching that branch to collapse dimensionless argument dimensions to Dimension(1) will make SI._collect_factor_and_dimension(100 + exp(expr)) succeed. Falsified if the ValueError still occurs after the check is added, or if is_dimensio

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: add-branch-equivalence-check

Alternative layer: instead of touching the Function branch, change the Add branch in _collect_factor_and_dimension (same file, lines 173-184) so the mismatch check does not use raw `dim != addend_dim` but instead uses the dimension system to test whether the two dimensions are equivalent (e.g. both 

**Hypothesis**: If the real defect is that dimension equality is too strict/naive (comparing Dimension objects structurally rather than via their dependency-collapsed dimensionality), then relaxing the Add-branch comparison to use dimension-system equivalence would fix the reported case without touching the Function branch. Falsified if exp(...)'s returned dimension is not literally dimensionless-equivalent to 1 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Sources consulted for branch check function

- issue.md reproduction + sympy/physics/units/unitsystem.py lines 152-200 read directly
- issue.md reproduction + sympy/physics/units/unitsystem.py lines 173-184

### X4 — What has been investigated about branch check function

Ground already covered by research on this subject.

- **function_branch_dim_computation** — In _collect_factor_and_dimension's `elif isinstance(expr, Function)` branch (unitsystem.py ~192-196), how should the returned dimension be computed so that when an argument's dimension is dimensionles
  Looked in: sympy/physics/units/unitsystem.py lines 152-200, specifically the Function branch
- **multi_arg_function_return_shape** — For multi-argument Functions (e.g. atan2), the current code returns `(expr.func(*(f[0] for f in fds)), *(d[1] for d in fds))` — a tuple of (factor, dim1, dim2, ...) instead of a 2-tuple (factor, dim).
  Looked in: sympy/physics/units/unitsystem.py lines 192-196; check with a quick reproduction using atan2 on current code before any fix
- **equality_semantics_of_dimensionless_dimension** — Does Dimension(1) == Dimension('time')/(Dimension('capacitance')*Dimension('impedance')) evaluate False even though get_dimension_system().is_dimensionless() is True for the latter? Confirm exactly wh
  Looked in: sympy/physics/units/dimensions.py Dimension.__eq__ and Dimension System is_dimensionless; sympy/physics/units/unitsystem.py get_dimensional_expr (~lines 143-150

...and 2 more line(s) of ground covered.

### X5 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **fraction_of_collect_factor_dimension_cases_correct** (max, target 1.0).

**Established**
- function-arg-dimensionless-check (working)

**Still open**
- add-branch-equivalence-check (potential)
- sympy/physics/units/unitsystem.py (potential fraction_of_collect_factor_dimension_cases_correct=1.0)
- aspect not yet answered: function_branch_dim_computation
- aspect not yet answered: multi_arg_function_return_shape
- aspect not yet answered: equality_semantics_of_dimensionless_dimension
- aspect not yet answered: existing_test_coverage_and_regressions

**Where the detail is**
- function-arg-dimensionless-check: issue.md reproduction + sympy/physics/units/unitsystem.py lines 152-200 read directly
- add-branch-equivalence-check: issue.md reproduction + sympy/physics/units/unitsystem.py lines 173-184
- sympy/physics/units/unitsystem.py: benchmark attempt
- full record: research topic `sympy__sympy-24066` (via research_status, only if this summary is not enough)