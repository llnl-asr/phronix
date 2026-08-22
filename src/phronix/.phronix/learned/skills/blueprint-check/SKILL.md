---
name: blueprint-check
description: Research on blueprint check. Covers what exception type and message convention does Flask already use for the analogous 1.0 check that rejects dots in endpoint names, so the new blueprint-name check matches project convention; where should the dot-in-name check live — Blueprint.__init__ (fails fast at construction) versus register()/make_setup_state (fails at registration time) — and does the existing nested-blueprint or register_blueprint code path already rely on constructing Blueprints with unchecked names internally (e.g. for name_prefix composition) in a way that a check in __init__ would
subject: blueprint-check
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to blueprint check |
| `I2` | Instructions | How to solve blueprint check |
| `I4` | Instructions | Steps to solve blueprint check |
| `X1` | References | Tried: blueprint-init-dot-check |
| `X2` | References | Tried: blueprint-register-dot-check |
| `X3` | References | Sources consulted for blueprint check |
| `X4` | References | What has been investigated about blueprint check |
| `X5` | References | Where research on this subject stands |
| `X8` | References | Tried: fix-sum-not-max-degree-filter-both-branches |
| `X9` | References | Tried: sum-powers-fix-passes-existing-tests-and-doctests |
| `X10` | References | Tried: sum_powers_no_subtraction |
| `X11` | References | Tried: doctest-set-ordering-failure-is-preexisting-not-regression |
| `X12` | References | Tried: subtract_sone_count_from_len_item |
| `X13` | References | Tried: sum-not-max-total-degree-filter |
| `X14` | References | Tried: rewrite-total-degree-branch-via-itermonomials-per-degree |




















































## Instructions

### I1 — How to evaluate a change to blueprint check

Figure of merit: **dot_in_blueprint_name_correctly_rejected_rate** (max, target 1.0).

Measured by: Fraction of corpus instances where constructing flask.Blueprint(name=..., import_name='x') raises ValueError iff name contains a '.', and does not raise for valid dotless names (including names with other special chars that should still be allowed), checked by running each instance's construction in a python snippet and asserting the observed raise/no-raise matches the expected outcome.

Cases differ along: dot_position, expected, name_form.

### I2 — How to solve blueprint check

Try these in order, ONE at a time. Ranked by measured **dot_in_blueprint_name_correctly_rejected_rate** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A1` **blueprint-init-dot-check** — dot_in_blueprint_name_correctly_rejected_rate unmeasured, potential — In Blueprint.__init__ (src/flask/blueprints.py), after self.name = name, raise ValueError 
2. `A2` **blueprint-register-dot-check** — dot_in_blueprint_name_correctly_rejected_rate unmeasured, potential — In Flask.register_blueprint / BlueprintSetupState (src/flask/blueprints.py or app.py), rai

...and 9 lower-ranked approach(es); see `research_rank`.### I3 — Fallback approaches for blueprint check

If the leading approach fails, these were also measured, ranked by the same metric.

**`A2` blueprint-register-dot-check** — dot_in_blueprint_name_correctly_rejected_rate unmeasured
  1. `probe_read_file_region(...)`
  2. Add dot validation at registration (judgement)
  3. `probe_run_pytest_selection(...)`
  4. `probe_run_python_snippet(...)`## Rules

### I4 — Steps to solve blueprint check

The steps that solve blueprint check, in order. Run them.

1. `probe_run_python_snippet(...)` — Reproduce the issue
2. `probe_find_call_sites(...)` — Locate the total-degree filter
3. **Diagnose semantics mismatch** (judgement — no tool for this)
   The docstring defines the filter as min_degree <= total_degree(monom) <= max_degree, i.e. total_degree = sum of exponents. The code used max(powers.values()) (largest single-variable exponent) instead
4. `probe_apply_text_replacement(...)` — Apply the fix to both branches
5. `probe_run_python_snippet(...)` — Verify against the issue reproducer
6. `probe_run_pytest_selection(...)` — Run existing regression tests and doctests### I5 — Fallback approaches for blueprint check

If the leading approach fails, these were also measured, ranked by the same metric.

**`A2` blueprint-register-dot-check** — dot_in_blueprint_name_correctly_rejected_rate unmeasured
  1. `probe_read_file_region(...)`
  2. Add dot validation at registration (judgement)
  3. `probe_run_pytest_selection(...)`
  4. `probe_run_python_snippet(...)`

**`A10` sum-not-max-total-degree-filter** — dot_in_blueprint_name_correctly_rejected_rate unmeasured
  1. Reproduce the issue (judgement)
  2. Locate the total-degree filter (judgement)
  3. Diagnose semantics mismatch (judgement)
  4. Apply the fix to both branches (judgement)
  5. Verify against the issue reproducer (judgement)
  6. Run existing regression tests and doctests (judgement)

**`A11` rewrite-total-degree-branch-via-itermonomials-per-degree** — dot_in_blueprint_name_correctly_rejected_rate unmeasured
  1. Reproduce the bug (judgement)
  2. Design degree-by-degree generation (judgement)
  3. Apply for both commutative and non-commutative cases (judgement)
  4. Verify against issue repro and existing docstring examples (judgement)
  5. Run existing test suite (judgement)
  6. Compare output sets against sum-based fix (A10) (judgement)## References

### X1 — Tried: blueprint-init-dot-check

In Blueprint.__init__ (src/flask/blueprints.py), after self.name = name, raise ValueError if "." in name.

**Hypothesis**: Blueprint names are validated once at construction time; adding a check right after self.name = name rejects dotted names for both top-level and nested blueprints uniformly. False if hidden tests expect the error only at registration time (register_blueprint) rather than construction.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: blueprint-register-dot-check

In Flask.register_blueprint / BlueprintSetupState (src/flask/blueprints.py or app.py), raise ValueError if "." in blueprint.name at registration time instead of construction.

**Hypothesis**: Validating at registration matches how nested-blueprint name_prefix composition happens (dots become meaningful only once registered/nested), so the check belongs where registration composes the full dotted name. False if construction-time check (blueprint-init-dot-check) already satisfies the hidden tests, making this unnecessary/duplicate work.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Sources consulted for blueprint check

- src/flask/blueprints.py Blueprint.__init__; issue references endpoint-name dot check added in Flask 1.0 (app.py add_url_rule) as precedent for placement at definition time
- src/flask/blueprints.py BlueprintSetupState/register_blueprint flow; issue mentions nested blueprints and name_prefix

### X4 — What has been investigated about blueprint check

Ground already covered by research on this subject.

- **error_type_and_message_convention** — What exception type and message convention does Flask already use for the analogous 1.0 check that rejects dots in endpoint names, so the new blueprint-name check matches project convention?
  Looked in: src/flask/blueprints.py add_url_rule (endpoint dot assert), src/flask/scaffold.py, CHANGES.rst history around 1.0
- **validation_placement** — Where should the dot-in-name check live — Blueprint.__init__ (fails fast at construction) versus register()/make_setup_state (fails at registration time) — and does the existing nested-blueprint or re
  Looked in: src/flask/blueprints.py Blueprint.__init__, Blueprint.register, BlueprintSetupState
- **existing_test_expectations** — Do the repository's own existing tests (tests/test_blueprints.py) already construct or register a Blueprint with a dot in its name anywhere (e.g. nested blueprint tests), which would need the fix to n
  Looked in: tests/test_blueprints.py### X5 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **dot_in_blueprint_name_correctly_rejected_rate** (max, target 1.0).

**Still open**
- pylint/lint/expand_modules.py (potential)
- blueprint-register-dot-check (potential)
- src/flask/blueprints.py (potential dot_in_blueprint_name_correctly_rejected_rate=1.0)
- aspect not yet answered: error_type_and_message_convention
- aspect not yet answered: validation_placement
- aspect not yet answered: existing_test_expectations

**Ruled out**
- blueprint-init-dot-check (failed) — try 1: target tests still failing: tests/test_blueprints.py::test_route_decorator_custom_e

**Where the detail is**
- pylint/lint/expand_modules.py: benchmark attempt
- blueprint-init-dot-check: src/flask/blueprints.py Blueprint.__init__; issue references endpoint-name dot check added in Flask 1.0 (app.p
- blueprint-register-dot-check: src/flask/blueprints.py BlueprintSetupState/register_blueprint flow; issue mentions nested blueprints and name
- src/flask/blueprints.py: benchmark attempt
- full record: research topic `pallets__flask-4045` (via research_status, only if this summary is not enough)

## References

### X5 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **dot_in_blueprint_name_correctly_rejected_rate** (max, target 1.0).

**Established**
- blueprint-init-dot-check (working)
- fix_total_degree_branch_only_max_to_sum (potential)
- apply_fix_to_list_form_branch_too (potential)
- fix-sum-not-max-degree-filter-both-branches (potential)
- sum-powers-fix-passes-existing-tests-and-doctests (potential)
- doctest-set-ordering-failure-is-preexisting-not-regression (potential)

**Still open**
- pylint/lint/expand_modules.py (potential)
- blueprint-register-dot-check (potential)
- sum_powers_no_subtraction (potential)
- subtract_sone_count_from_len_item (potential)
- rewrite-total-degree-branch-via-itermonomials-per-degree (potential)
- sympy/polys/monomials.py (potential dot_in_blueprint_name_correctly_rejected_rate=1.0)

**Where the detail is**
- pylint/lint/expand_modules.py: benchmark attempt
- blueprint-init-dot-check: src/flask/blueprints.py Blueprint.__init__; issue references endpoint-name dot check added in Flask 1.0 (app.p
- blueprint-register-dot-check: src/flask/blueprints.py BlueprintSetupState/register_blueprint flow; issue mentions nested blueprints and name

...and 4 more line(s); see the full record.### X7 — Tried: apply_fix_to_list_form_branch_too

REJECTED/refuted candidate: modifying or worrying about the list-form (Case II, max_degrees/min_degrees as lists) branch as part of this fix. Investigation showed this branch uses entirely separate logic (power_lists / Cartesian product over explicit per-variable ranges via zip(variables, min_degree

**Hypothesis**: Hypothesis considered and refuted: that the max-vs-sum bug might also affect or require a matching fix in the list-form branch, since both branches conceptually filter monomials by degree. Refuted by: reading the list-form branch code (lines 145-150) which has no max()/sum()/powers-dict pattern; and by direct testing — the list-form branch docstring example (itermonomials([x,y],[2,4],[1,2])) produ

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: fix-sum-not-max-degree-filter-both-branches

Apply sum(powers.values()) >= min_degree in place of max(powers.values()) >= min_degree to BOTH the commutative and non-commutative loops of itermonomials's total_degree branch in sympy/polys/monomials.py (~lines 130 and 142). Verified: 11/11 existing tests pass (sympy/polys/tests/test_monomials.py)

**Hypothesis**: The original bug (max() instead of sum() when checking min_degree) is structurally identical in both the commutative and non-commutative loops, so the same one-line fix applies verbatim to each; would be falsified if the two branches differ in variable set (e.g. S.One handling) requiring different logic per branch, or if applying it broke existing tests.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Tried: sum-powers-fix-passes-existing-tests-and-doctests

Changing max(powers.values()) to sum(powers.values()) in itermonomials() (both commutative and non-commutative total_degree branches, sympy/polys/monomials.py ~lines 137,142) is fully compatible with existing tests and doctests. All 11 tests in test_monomials.py pass unchanged (none of the min_degre

**Hypothesis**: The buggy filter `max(powers.values()) >= min_degree` checks max single-variable exponent instead of total degree, violating the documented contract `min_degree <= total_degree(monom) <= max_degree`. Hypothesis: replacing max() with sum() fixes this without breaking any existing test/doctest, because no existing assertion exercises a genuinely multivariate min_degree case where max-power and total

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X10 — Tried: sum_powers_no_subtraction

Fix itermonomials total_degree branch by replacing max(powers.values()) with sum(powers.values()) in both the commutative (combinations_with_replacement) and non-commutative (product) branches of sympy/polys/monomials.py. No extra subtraction of S.One's count from len(item) is needed: powers is keye

**Hypothesis**: H: sum(powers.values()) alone (no len(item)-powers[S.One] adjustment) equals the true total degree for every combinations_with_replacement/product item, because the loop never increments powers[S.One]. Falsified if any item showed powers[S.One] > 0, or if sum(powers.values()) != true degree in reproduction — neither occurred in manual trace or itermonomials([x,y],3,2) check.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X11 — Tried: doctest-set-ordering-failure-is-preexisting-not-regression

The doctest `set(itermonomials([a, b, x], 2))` (noncommutative case, no min_degree) reports a doctest "failure" both before and after the fix, due to Python set iteration/repr order being hash-seed dependent — not due to content differences. This is NOT a regression introduced by the total_degree fi

**Hypothesis**: Hypothesis considered: the observed doctest mismatch on the noncommutative set-based example is caused by the max->sum fix. Refuted by: stashing the fix and re-running the identical doctest against unmodified/original code — the same kind of ordering mismatch occurs there too (different order, same class of failure), proving it's a pre-existing environment-dependent fragility unrelated to the fix.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X12 — Tried: subtract_sone_count_from_len_item

REFUTED: hypothesized that the fix needs something like `len(item) - powers[S.One]` (or equivalent explicit subtraction of S.One's count) to compute true total degree, on the theory that S.One padding entries in `item` might inflate powers.values(). Refuted by tracing the code: the inner loop `for v

**Hypothesis**: H: the correct fix requires explicitly subtracting S.One's padding count from len(item)/sum to get true degree. Falsified: powers[S.One] is always 0 in this code path (verified by trace and manual example), so plain sum(powers.values()) is already correct and no subtraction term exists to add.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X13 — Tried: sum-not-max-total-degree-filter

In sympy/polys/monomials.py itermonomials, total_degree branch (lines ~121-144): replace `max(powers.values()) >= min_degree` with `sum(powers.values()) >= min_degree` in both the commutative (line 130) and non-commutative (line 142) loops.

**Hypothesis**: The filter checks the max single-variable exponent instead of the total degree (sum of exponents), so monomials like x1*x2**2 (total degree 3, but max exponent 2) are wrongly excluded when min_degree=3. True if sum(powers.values()) equals the actual total degree of each generated item (it does, since items are always length max_degree with S.One padding). False if hidden tests expect something els

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X14 — Tried: rewrite-total-degree-branch-via-itermonomials-per-degree

Instead of patching the existing max()-based filter, rewrite the total_degree branch of itermonomials to loop over each degree d from min_degree to max_degree and union combinations_with_replacement(variables, d) directly (no S.One padding/powers-dict filtering needed), building the monomial set deg

**Hypothesis**: Generating monomials degree-by-degree via combinations_with_replacement(variables, d) for d in range(min_degree, max_degree+1) is a structurally different, arguably clearer way to guarantee exact total-degree correctness, avoiding the powers-dict/S.One padding trick entirely. False if this changes generator ordering/behavior in a way that breaks existing doctests expecting specific output structur

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.
