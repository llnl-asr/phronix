---
name: sympy
description: Research on sympy. Covers where in the Sympy codebase is the faulty behavior of SI._collect_factor_and_dimension produced; what is the smallest reproducible example that triggers the dimensionless exponent bug; which existing test(s) cover the behavior of SI._collect_factor_and_dimension and what do they assert. Approaches tried: handle_exp_dimensionless, add_exp_case_in_unitsystem.
subject: sympy
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to sympy |
| `I2` | Instructions | How to solve sympy |
| `I3` | Instructions | Steps to solve sympy |
| `X1` | References | Tried: handle_exp_dimensionless |
| `X2` | References | Tried: add_exp_case_in_unitsystem |
| `X3` | References | Sources consulted for sympy |
| `X4` | References | What has been investigated about sympy |








## Instructions

### I1 — How to evaluate a change to sympy

Figure of merit: **bug_failure_count** (min, target 0.0).

Measured by: Count how many corpus instances raise a ValueError when calling SI._collect_factor_and_dimension on the provided expression; lower count is better, target 0 failures.

Cases differ along: expr_type, operation, should_be_dimensionless, units_form.

### I2 — How to solve sympy

Try these in order, ONE at a time. Ranked by measured **bug_failure_count** (min, target 0.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A1` **handle_exp_dimensionless** — bug_failure_count unmeasured, potential — Update _collect_factor_and_dimension to treat exp() as dimensionless when argument is dime
2. `A2` **add_exp_case_in_unitsystem** — bug_failure_count unmeasured, potential — Add explicit handling for exp() in UnitSystem._collect_factor_and_dimension to treat it as

### I3 — Steps to solve sympy

The steps that solve sympy, in order. Run them.

1. `probe_find_call_sites(...)` — Locate exp handling in UnitSystem._collect_factor_and_dimension
2. `probe_apply_and_score(...)` — Patch exp handling to treat dimensionless arguments as dimensionless result
3. `probe_run_pylint_check(...)` — Run unit tests for exp handling

## Rules

## References

### X1 — Tried: handle_exp_dimensionless

Update _collect_factor_and_dimension to treat exp() as dimensionless when argument is dimensionless.

**Hypothesis**: If _collect_factor_and_dimension returns dimensionless for exp(dimless_arg), the bug will be resolved.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: add_exp_case_in_unitsystem

Add explicit handling for exp() in UnitSystem._collect_factor_and_dimension to treat it as dimensionless when its argument is dimensionless.

**Hypothesis**: If we add a branch that checks for sympy.exp and returns (1, Dimension(1)) when argument dimension is dimensionless, the bug will be fixed.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Sources consulted for sympy

- Sympy issue 24066 and typical unit system implementation patterns
- issue sympy-24066 reporting dimensionless exponent failure

### X4 — What has been investigated about sympy

Ground already covered by research on this subject.

- **code-location** — Where in the Sympy codebase is the faulty behavior of SI._collect_factor_and_dimension produced?
- **reproduction** — What is the smallest reproducible example that triggers the dimensionless exponent bug?
- **test-coverage** — Which existing test(s) cover the behavior of SI._collect_factor_and_dimension and what do they assert?
- **minimal-fix** — What is the smallest correct code change to fix the bug, and what risks does it introduce?
