---
name: degree-padding
description: Research on degree padding. Covers in the total_degree (integer max_degrees) branch of itermonomials (sympy/polys/monomials.py, both the commutative and non-commutative loops), the filter `if max(powers.values()) >= min_degree` uses the MAX single-variable power rather than the SUM of powers (total degree). Confirm this is the actual defect by tracing why it produces only x1**3,x2**3,x3**3 for the issue's example and not mixed terms, and confirm the correct condition is total degree (sum of powers over non-padding variables, i.e. len(item) since combinations_with_replacement already fixes tota
subject: degree-padding
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to degree padding |
| `I2` | Instructions | How to solve degree padding |
| `I4` | Instructions | Steps to solve degree padding |
| `X1` | References | Tried: fix-sum-not-max-degree-filter |
| `X2` | References | Tried: explicit-degree-loop-no-padding |
| `X3` | References | Sources consulted for degree padding |
| `X4` | References | What has been investigated about degree padding |
| `X5` | References | Where research on this subject stands |























## Instructions

### I1 — How to evaluate a change to degree padding

Figure of merit: **itermonomials_correctness_rate** (max, target 1.0).

Measured by: For each corpus instance, call sp.itermonomials(variables, max_degrees, min_degrees=min_degrees) (integer or list form as specified), collect the resulting set of monomials, and compare it to the expected set computed independently (e.g. via itertools.combinations_with_replacement over variables+[1] filtered by total_degree for the integer case, or itertools.product over per-variable power ranges 

Cases differ along: case_type, commutativity, degree_form, min_max_relation, num_variables.

### I2 — How to solve degree padding

Try these in order, ONE at a time. Ranked by measured **itermonomials_correctness_rate** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A1` **fix-sum-not-max-degree-filter** — itermonomials_correctness_rate unmeasured, potential — Edit sympy/polys/monomials.py: in both the commutative and non-commutative branches of the
2. `A2` **explicit-degree-loop-no-padding** — itermonomials_correctness_rate unmeasured, potential — Rewrite the total_degree branch in sympy/polys/monomials.py to iterate d from min_degree t### I3 — Fallback approaches for degree padding

If the leading approach fails, these were also measured, ranked by the same metric.

**`A2` explicit-degree-loop-no-padding** — itermonomials_correctness_rate unmeasured
  1. `grep_locate_line(...)`
  2. `python_expect_exception(...)`
  3. Rewrite commutative branch as degree loop (judgement)
  4. Rewrite non-commutative branch as degree loop (judgement)
  5. Handle edge cases (judgement)
  6. `probe_run_doctest_module(...)`
  7. `probe_run_pytest_selection(...)`## Rules

### I4 — Steps to solve degree padding

The steps that solve degree padding, in order. Run them.

1. `grep_locate_line(...)` — Read itermonomials source
2. `python_expect_exception(...)` — Reproduce issue
3. **Fix commutative branch filter** (judgement — no tool for this)
   Replace max(powers.values()) >= min_degree with sum(powers.values()) >= min_degree (excluding the appended S.One padding variable) in the commutative branch
4. **Fix non-commutative branch filter** (judgement — no tool for this)
   Apply the same sum-not-max correction to the non-commutative branch's min_degree filter
5. `probe_run_doctest_module(...)` — Verify fix and docstring examples
6. `probe_run_pytest_selection(...)` — Run existing test suite### I5 — Fallback approaches for degree padding

If the leading approach fails, these were also measured, ranked by the same metric.

**`A2` explicit-degree-loop-no-padding** — itermonomials_correctness_rate unmeasured
  1. `grep_locate_line(...)`
  2. `python_expect_exception(...)`
  3. Rewrite commutative branch as degree loop (judgement)
  4. Rewrite non-commutative branch as degree loop (judgement)
  5. Handle edge cases (judgement)
  6. `probe_run_doctest_module(...)`
  7. `probe_run_pytest_selection(...)`## References

### X1 — Tried: fix-sum-not-max-degree-filter

Edit sympy/polys/monomials.py: in both the commutative and non-commutative branches of the total_degree case, change the min_degree comparison from max(powers.values()) to sum of powers over the real variables (excluding the appended S.One), so it matches the documented total_degree(monom) semantics

**Hypothesis**: The filter `max(powers.values()) >= min_degree` in itermonomials' total_degree branch checks the highest single-variable exponent instead of total degree (sum of exponents), so mixed-degree monomials like x1*x2**2 are dropped. Replacing with sum(powers.values()) >= min_degree (excluding the S.One padding variable) fixes both commutative and non-commutative branches. Falsifiable: after the fix, ite

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: explicit-degree-loop-no-padding

Rewrite the total_degree branch in sympy/polys/monomials.py to iterate d from min_degree to max_degree, and for each d use combinations_with_replacement(variables, d) (no S.One padding) to build Mul(*item), unioning into the result set, for both commutative and non-commutative cases.

**Hypothesis**: Instead of patching the min_degree filter, replace the padding-trick (appending S.One and using combinations_with_replacement(variables+[1], max_degree)) with a direct loop over each degree d in range(min_degree, max_degree+1), generating combinations_with_replacement(variables, d) for that exact degree and unioning results. This sidesteps the padding-variable bookkeeping entirely and is falsifiab

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Sources consulted for degree padding

- sympy/polys/monomials.py itermonomials total_degree branch; issue text
- sympy/polys/monomials.py itermonomials, lines ~121-144; issue text

### X4 — What has been investigated about degree padding

Ground already covered by research on this subject.

- **root_cause_condition** — In the total_degree (integer max_degrees) branch of itermonomials (sympy/polys/monomials.py, both the commutative and non-commutative loops), the filter `if max(powers.values()) >= min_degree` uses th
  Looked in: sympy/polys/monomials.py itermonomials, total_degree branch, both commutative and non-commutative loops
- **padding_variable_interaction** — variables is padded with an extra S.One before combinations_with_replacement/product so that combinations of length < max_degree can be represented (the '1' fills unused slots). Does the min_degree ch
  Looked in: sympy/polys/monomials.py itermonomials, variables = list(variables) + [S.One] line and the two loops after it
- **minimal_fix_scope** — What is the smallest correct change to the filter condition (and does it differ between the commutative and non-commutative branches, given item is a tuple of length max_degree drawn with replacement/
  Looked in: sympy/polys/monomials.py itermonomials, both branches under `if total_degree:`
- **existing_test_coverage** — What do sympy's existing tests in sympy/polys/tests/test_monomials.py assert about itermonomials with min_degrees, and would a naive fix (e.g. only fixing the min==max case) still pass those tests whi

...and 1 more line(s) of ground covered.

## References

### X5 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **itermonomials_correctness_rate** (max, target 1.0).

**Established**
- fix-sum-not-max-degree-filter (working)

**Still open**
- explicit-degree-loop-no-padding (potential)
- pylint/checkers/misc.py (potential itermonomials_correctness_rate=1.0)
- aspect not yet answered: padding_variable_interaction
- aspect not yet answered: existing_test_coverage

**Where the detail is**
- fix-sum-not-max-degree-filter: sympy/polys/monomials.py itermonomials, lines ~121-144; issue text
- explicit-degree-loop-no-padding: sympy/polys/monomials.py itermonomials total_degree branch; issue text
- pylint/checkers/misc.py: benchmark attempt
- full record: research topic `sympy__sympy-21847` (via research_status, only if this summary is not enough)