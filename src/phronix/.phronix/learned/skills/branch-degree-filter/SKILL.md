---
name: branch-degree-filter
description: Research on branch degree filter. Covers in the total_degree=True branch of itermonomials (sympy/polys/monomials.py, commutative loop around line 122-131), the filter `if max(powers.values()) >= min_degree` checks the MAX exponent of any single variable rather than the sum of exponents (total degree) of the actual variables (excluding the padding S.One). What is the correct replacement expression, and does it need `max_degree - powers[S.One]` or an equivalent sum-of-non-one-powers computation to correctly implement min_degree <= total_degree(monom) <= max_degree; does the non-commutative loop 
subject: branch-degree-filter
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to branch degree filter |
| `I2` | Instructions | How to solve branch degree filter |
| `I3` | Instructions | Steps to solve branch degree filter |
| `X1` | References | Tried: fix-sum-not-max-degree-filter |
| `X2` | References | Tried: explicit-degree-loop-no-padding |
| `X3` | References | Sources consulted for branch degree filter |
| `X4` | References | What has been investigated about branch degree filter |
| `X5` | References | Where research on this subject stands |











## Instructions

### I1 — How to evaluate a change to branch degree filter

Figure of merit: **itermonomials_correctness_rate** (max, target 1.0).

Measured by: Fraction of corpus instances where set(itermonomials(variables, max_degrees, min_degrees=min_degrees)) exactly equals the expected monomial set (computed independently via brute-force: for total-degree case, all monomials in `variables` with total_degree in [min_degree, max_degree]; for per-variable list case, all monomials with each exponent in [min_degrees[i], max_degrees[i]]). Run each instance

Cases differ along: commutativity, degree_form, expected_result, min_max_relation, num_variables.

### I2 — How to solve branch degree filter

Try these in order, ONE at a time. Ranked by measured **itermonomials_correctness_rate** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A1` **fix-sum-not-max-degree-filter** — itermonomials_correctness_rate unmeasured, potential — In sympy/polys/monomials.py itermonomials total_degree branch (both commutative and non-co
2. `A2` **explicit-degree-loop-no-padding** — itermonomials_correctness_rate unmeasured, potential — Rewrite the total_degree branch in sympy/polys/monomials.py to iterate d from min_degree t

### I3 — Steps to solve branch degree filter

The steps that solve branch degree filter, in order. Run them.

1. `find_symbol_definition(...)` — Locate itermonomials total_degree branch
2. `probe_run_python_snippet(...)` — Reproduce the issue
3. **Fix commutative branch filter** (judgement — no tool for this)
   Replace `if max(powers.values()) >= min_degree:` with a total-degree sum check over the real variables (excluding the appended S.One padding entry), e.g. `if sum(powers[v] for v in variables if v != S
4. **Fix non-commutative branch filter** (judgement — no tool for this)
   Apply the identical sum-not-max correction to the non-commutative branch's min_degree filter
5. `probe_run_doctest_module(...)` — Verify docstring examples still valid
6. `probe_run_pytest_selection(...)` — Run existing test suite

## Rules

## References

### X1 — Tried: fix-sum-not-max-degree-filter

In sympy/polys/monomials.py itermonomials total_degree branch (both commutative and non-commutative loops), replace `if max(powers.values()) >= min_degree` with a total-degree check: sum(powers.values()) over the real variables (excluding the appended S.One padding entry) compared against min_degree

**Hypothesis**: The filter uses max single-variable exponent instead of sum of exponents (total degree), so mixed-degree monomials like x1*x2**2 get dropped when min_degree==max_degree. Falsifiable: after the fix, itermonomials([x1,x2,x3],3,min_degrees=3) should include x1*x2**2 etc, not just pure powers.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: explicit-degree-loop-no-padding

Rewrite the total_degree branch in sympy/polys/monomials.py to iterate d from min_degree to max_degree, and for each d use combinations_with_replacement(variables, d) (no S.One padding) for commutative, or product(variables, repeat=d) for non-commutative, building Mul(*item) and unioning results acr

**Hypothesis**: Replacing the padding-trick with a direct per-degree loop avoids padding-variable bookkeeping entirely and is correct by construction since each d directly controls total degree. Falsifiable the same way as the filter fix: check the resulting monomial set matches the documented min_degree<=total_degree<=max_degree condition.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Sources consulted for branch degree filter

- degree-padding skill (prior research), sympy/polys/monomials.py lines ~121-144, issue.md

### X4 — What has been investigated about branch degree filter

Ground already covered by research on this subject.

- **total_degree_filter_bug** — In the total_degree=True branch of itermonomials (sympy/polys/monomials.py, commutative loop around line 122-131), the filter `if max(powers.values()) >= min_degree` checks the MAX exponent of any sin
  Looked in: sympy/polys/monomials.py lines 113-146 (itermonomials total_degree branch, both commutative and non-commutative loops)
- **noncommutative_branch_same_bug** — Does the non-commutative loop (product(variables, repeat=max_degree) branch, roughly lines 133-146) have the identical incorrect filter, and does the same fix pattern apply there without altering its 
  Looked in: sympy/polys/monomials.py non-commutative loop, ~lines 133-146
- **per_variable_list_branch_correctness** — Is the Case II (max_degrees/min_degrees as lists, per-variable bounds) branch of itermonomials already correct and unaffected by this bug, i.e. does it use a straightforward per-exponent product/range
  Looked in: sympy/polys/monomials.py, the branch handling is_sequence(max_degrees)==True
- **existing_test_coverage_gap** — What does sympy/polys/tests/test_monomials.py currently test for itermonomials with min_degrees, and does it already cover (or fail to cover) the min==max total-degree case that exposes this bug, so w

...and 1 more line(s) of ground covered.

### X5 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **itermonomials_correctness_rate** (max, target 1.0).

**Established**
- fix-sum-not-max-degree-filter (working)

**Still open**
- explicit-degree-loop-no-padding (potential)
- aspect not yet answered: total_degree_filter_bug
- aspect not yet answered: noncommutative_branch_same_bug
- aspect not yet answered: per_variable_list_branch_correctness
- aspect not yet answered: existing_test_coverage_gap

**Where the detail is**
- fix-sum-not-max-degree-filter: degree-padding skill (prior research), sympy/polys/monomials.py lines ~121-144, issue.md
- explicit-degree-loop-no-padding: degree-padding skill (prior research), sympy/polys/monomials.py itermonomials total_degree branch
- full record: research topic `sympy__sympy-21847` (via research_status, only if this summary is not enough)