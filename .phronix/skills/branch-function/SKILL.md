---
name: branch-function
description: Research on branch function. Covers what should the Function branch of UnitSystem._collect_factor_and_dimension return for dimension when expr is an arbitrary sympy Function (exp, log, sin, cos, atan2, ...) — should it require ALL arguments to be dimensionless and then always return Dimension(1) for the whole call, or is there a class of functions (e.g. Abs, Max, Min, sign) where the output dimension should instead equal the (common) input dimension rather than being forced dimensionless? Look at how Abs/Max/Min are handled elsewhere in the units system (e.g. any special-casing in unitsystem.p
subject: branch-function
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to branch function |
| `I2` | Instructions | How to solve branch function |
| `I3` | Instructions | Fallback approaches for branch function |
| `I4` | Instructions | Steps to solve branch function |
| `X1` | References | Tried: function-branch-dimensionless-check |
| `X2` | References | Tried: function-branch-raise-on-nondimensionless |
| `X3` | References | Sources consulted for branch function |
| `X4` | References | What has been investigated about branch function |
| `X5` | References | Where research on this subject stands |

















## Instructions

### I1 — How to evaluate a change to branch function

Figure of merit: **fraction_of_test_instances_where_collect_factor_and_dimension_matches_expected** (max, target 1.0).

Measured by: For each corpus instance, call SI._collect_factor_and_dimension(expr) (or the relevant UnitSystem instance) on the given expression and compare the returned (factor, dimension) pair — or the raised exception — against the expected outcome recorded for that instance (either a specific Dimension e.g. Dimension(1)/dimensionless, or 'raises ValueError'). Score = (# instances where actual matches expec

Cases differ along: expr_kind, function_used, nesting_depth, should_error.

### I2 — How to solve branch function

Try these in order, ONE at a time. Ranked by measured **fraction_of_test_instances_where_collect_factor_and_dimension_matches_expected** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A1` **function-branch-dimensionless-check** — fraction_of_test_instances_where_collect_factor_and_dimension_matches_expected unmeasured, potential — In sympy/physics/units/unitsystem.py `_collect_factor_and_dimension`, fix the `Function` b

...and 1 lower-ranked approach(es); see `research_rank`.

### I3 — Fallback approaches for branch function

If the leading approach fails, these were also measured, ranked by the same metric.

**`A2` function-branch-raise-on-nondimensionless** — fraction_of_test_instances_where_collect_factor_and_dimension_matches_expected unmeasured
  1. `find_symbol_definition(...)`
  2. Edit Function branch with explicit raise (judgement)
  3. `probe_reproduce_dimension_issue(...)`
  4. `probe_run_python_snippet(...)`
  5. `probe_run_pytest_selection(...)`## Rules

### I4 — Steps to solve branch function

The steps that solve branch function, in order. Run them.

1. `find_symbol_definition(...)` — Read current Function branch
2. **Edit Function branch** (judgement — no tool for this)
   Replace the Function branch: compute (factor, dim) for each arg via self._collect_factor_and_dimension(arg), verify each dim is dimensionless via self.get_dimension_system().is_dimensionless(dim), rai
3. `probe_reproduce_dimension_issue(...)` — Reproduce issue script
4. `probe_run_pytest_selection(...)` — Run existing unit system tests
5. **Check other Function usages** (judgement — no tool for this)
   Confirm no other passing test depends on Function branch returning non-dimensionless dims

## References

### X1 — Tried: function-branch-dimensionless-check

In sympy/physics/units/unitsystem.py `_collect_factor_and_dimension`, fix the `Function` branch (lines 192-196) to check each argument's dimension is dimensionless via `self.get_dimension_system().is_dimensionless(d[1])`, raising ValueError if not, and return `(expr.func(*(f[0] for f in fds)), Dimen

**Hypothesis**: The Function branch's bug is twofold: (1) it never validates argument dimensionlessness like Pow does, and (2) it returns a malformed tuple (factor, dim1, dim2, ...) for multi-arg functions instead of (factor, dimension). Fixing both by validating each arg is dimensionless and always returning Dimension(1) as the dimension will make exp(second/(farad*ohm)) correctly resolve to Dimension(1) instead

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: function-branch-raise-on-nondimensionless

Same location (Function branch, unitsystem.py ~192-196), but instead of silently forcing Dimension(1), explicitly raise ValueError with a descriptive message when an argument's dimension is not dimensionless (mirroring the Add branch's error style), and only return Dimension(1) when validation passe

**Hypothesis**: Users/tests may expect a clear ValueError (like the Add branch produces) when calling e.g. exp(meter) directly, not just silent coercion. This differs from the first approach in strictness/error messaging; if repo tests check for a specific error message format on invalid Function args, this is necessary. False if no such test exists and simple coercion suffices.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Sources consulted for branch function

- Direct code reading of unitsystem.py lines 152-200; issue.md reproduction

### X4 — What has been investigated about branch function

Ground already covered by research on this subject.

- **function_branch_semantics** — What should the Function branch of UnitSystem._collect_factor_and_dimension return for dimension when expr is an arbitrary sympy Function (exp, log, sin, cos, atan2, ...) — should it require ALL argum
  Looked in: sympy/physics/units/unitsystem.py Function branch; sympy/physics/units/tests/test_quantities.py existing Function-related tests
- **multiarg_and_mismatched_dim_functions** — For a multi-argument function like atan2/Max/Min where arguments have DIFFERENT but individually non-dimensionless dimensions, should _collect_factor_and_dimension raise ValueError (mirroring how the 
  Looked in: sympy/physics/units/unitsystem.py Add branch (existing ValueError raising code) as the template for Function-branch error handling
- **upstream_fix_reference** — Does the actual upstream SymPy fix for this issue (GitHub issue/PR around sympy/sympy#24065-24066) simply change the Function branch to check is_dimensionless on each arg's dimension and return Dimens
  Looked in: git log --all --grep for 24066/24065/collect_factor_and_dimension; sympy/physics/units/unitsystem.py git blame history if the fix commit exists in a later fetch

### X5 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **fraction_of_test_instances_where_collect_factor_and_dimension_matches_expected** (max, target 1.0).

**Still open**
- function-branch-dimensionless-check (potential)
- function-branch-raise-on-nondimensionless (potential)
- aspect not yet answered: function_branch_semantics
- aspect not yet answered: multiarg_and_mismatched_dim_functions
- aspect not yet answered: upstream_fix_reference

**Where the detail is**
- function-branch-dimensionless-check: Direct code reading of unitsystem.py lines 152-200; issue.md reproduction
- function-branch-raise-on-nondimensionless: Pattern from Add branch error handling (lines 178-182) in same file
- full record: research topic `sympy__sympy-24066` (via research_status, only if this summary is not enough)