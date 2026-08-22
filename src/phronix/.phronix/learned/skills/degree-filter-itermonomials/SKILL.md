---
name: degree-filter-itermonomials
description: Research on degree filter itermonomials. Covers confirm the exact defect: in sympy/polys/monomials.py total_degree branch, does `max(powers.values()) >= min_degree` incorrectly filter by the max single-variable exponent instead of the monomial's true total degree (sum of powers over real variables, excluding the appended S.One padding)? Verify by reading the code and reproducing the issue's example.; what is the correct replacement condition, and does it need to account for the S.One padding variable (which must not count toward total degree) and work identically for both the commutative combi
subject: degree-filter-itermonomials
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to degree filter itermonomials |
| `I2` | Instructions | How to solve degree filter itermonomials |
| `I4` | Instructions | Steps to solve degree filter itermonomials |
| `X1` | References | Tried: fix-total-degree-check-in-itermonomials |
| `X2` | References | Tried: fix-max-to-sum-in-commutative-filter |
| `X3` | References | Tried: same-sum-fix-for-noncommutative-branch |
| `X4` | References | Tried: fix-min-degree-check-total-degree |
| `X5` | References | Tried: list-based-min-degrees-branch-is-buggy |
| `X6` | References | Tried: fix-max-to-sum-in-itermonomials-degree-filter |
| `X7` | References | Tried: sum-minus-powers-of-one-in-itermonomials-degree-filter |
| `X8` | References | Tried: restructure-per-degree-generation |
| `X9` | References | Tried: stars-and-bars-exponent-tuples |
| `X10` | References | Sources consulted for degree filter itermonomials |
| `X11` | References | What has been investigated about degree filter itermonomials |
| `X12` | References | Where research on this subject stands |





































## Instructions

### I1 — How to evaluate a change to degree filter itermonomials

Figure of merit: **itermonomials_correctness_rate** (max, target 1.0).

Measured by: Fraction of corpus instances where set(itermonomials(*args)) exactly equals the expected monomial set (computed independently via combinations_with_replacement/product + true total-degree sum, not via max(powers)), checked with sympy's Eq/set equality after running each instance's command in-repo.

Cases differ along: commutativity, degree_mode, expected_result, min_max_relation, num_variables.

### I2 — How to solve degree filter itermonomials

Try these in order, ONE at a time. Ranked by measured **itermonomials_correctness_rate** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A1` **fix-total-degree-check-in-itermonomials** — itermonomials_correctness_rate unmeasured, potential — Replace `max(powers.values()) >= min_degree` with total-degree check `sum(powers.values())
2. `A2` **fix-max-to-sum-in-commutative-filter** — itermonomials_correctness_rate unmeasured, potential — In itermonomials (sympy/polys/monomials.py, total_degree=True commutative branch, ~line 13

...and 7 lower-ranked approach(es); see `research_rank`.### I3 — Fallback approaches for degree filter itermonomials

If the leading approach fails, these were also measured, ranked by the same metric.

**`A8` restructure-per-degree-generation** — itermonomials_correctness_rate unmeasured
  1. `probe_find_call_sites(...)`
  2. `probe_apply_text_replacement(...)`
  3. `probe_apply_text_replacement(...)`
  4. Handle the max_degree==0 / empty-variables special case (sti (judgement)
  5. `probe_run_python_snippet(...)`
  6. `probe_run_pytest_selection(...)`

**`A9` stars-and-bars-exponent-tuples** — itermonomials_correctness_rate unmeasured
  1. Locate itermonomials total_degree branch (commutative & non- (judgement)
  2. Write a stars-and-bars generator: for a given degree d and n (judgement)
  3. Replace commutative branch body with: for d in range(min_deg (judgement)
  4. For non-commutative branch, reuse per-degree product(variabl (judgement)
  5. Handle max_degree==0 / empty-variables special case (yield S (judgement)
  6. Run the issue reproduction snippet and confirm all total-deg (judgement)
  7. Run sympy/polys/tests/test_monomials.py and doctests in mono (judgement)## Rules

### I4 — Steps to solve degree filter itermonomials

The steps that solve degree filter itermonomials, in order. Run them.

1. `probe_find_call_sites(...)` — Locate itermonomials total_degree branch (commutative & non-commutative) in sympy/polys/monomials.py
2. `probe_apply_text_replacement(...)` — Remove the S.One padding of variables and the powers-dict >= min_degree filter
3. `probe_apply_text_replacement(...)` — Replace fixed-length combinations_with_replacement/product with a per-degree loop over range(min_degree, max_degree+1)
4. **Handle the max_degree==0 / empty-variables special case (still yield S.One) consistent with min_degree<=0** (judgement — no tool for this)
   Decide how to special-case degree 0 so S.One is yielded when min_degree<=0<=max_degree, matching prior documented behavior.
5. `probe_run_python_snippet(...)` — Run the issue reproduction snippet (min_degrees=3, max_degrees=3, 3 vars) and confirm all total-degree-3 monomials appear
6. `probe_run_pytest_selection(...)` — Run sympy/polys/tests/test_monomials.py and doctests in monomials.py to check no regressions### I5 — Fallback approaches for degree filter itermonomials

If the leading approach fails, these were also measured, ranked by the same metric.

**`A8` restructure-per-degree-generation** — itermonomials_correctness_rate unmeasured
  1. `probe_find_call_sites(...)`
  2. `probe_apply_text_replacement(...)`
  3. `probe_apply_text_replacement(...)`
  4. Handle the max_degree==0 / empty-variables special case (sti (judgement)
  5. `probe_run_python_snippet(...)`
  6. `probe_run_pytest_selection(...)`

**`A9` stars-and-bars-exponent-tuples** — itermonomials_correctness_rate unmeasured
  1. Locate itermonomials total_degree branch (commutative & non- (judgement)
  2. Write a stars-and-bars generator: for a given degree d and n (judgement)
  3. Replace commutative branch body with: for d in range(min_deg (judgement)
  4. For non-commutative branch, reuse per-degree product(variabl (judgement)
  5. Handle max_degree==0 / empty-variables special case (yield S (judgement)
  6. Run the issue reproduction snippet and confirm all total-deg (judgement)
  7. Run sympy/polys/tests/test_monomials.py and doctests in mono (judgement)## References

### X1 — Tried: fix-total-degree-check-in-itermonomials

Replace `max(powers.values()) >= min_degree` with total-degree check `sum(powers.values()) - powers[S.One] >= min_degree` in both commutative and non-commutative branches of itermonomials (sympy/polys/monomials.py)

**Hypothesis**: The min_degree filter in the total_degree branch of itermonomials wrongly uses the max single-variable exponent instead of the monomial's total degree, causing mixed-variable monomials (e.g. x1*x2**2) to be dropped when min_degree==max_degree. If true, changing the filter to total degree (max_degree - powers[S.One]) will produce the full correct set of monomials and not break existing tests.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: fix-max-to-sum-in-commutative-filter

In itermonomials (sympy/polys/monomials.py, total_degree=True commutative branch, ~line 130), change `if max(powers.values()) >= min_degree:` to `if sum(powers.values()) >= min_degree:`. Experimentally verified: fixes the repro case, producing all 10 correct degree-3 monomials in x1,x2,x3 instead of

**Hypothesis**: The filter should test total degree (sum of exponents) against min_degree, not the max single-variable exponent. max() wrongly drops mixed-variable monomials (e.g. x1*x2**2) whose total degree equals min_degree but whose largest single exponent is less than min_degree. Falsified if a sum()-based filter fails to reproduce the expected monomial set or breaks existing itermonomials tests.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: same-sum-fix-for-noncommutative-branch

The non-commutative branch (monomials_list_non_comm, using product() instead of combinations_with_replacement, ~lines 136-142) has the structurally identical `max(powers.values()) >= min_degree` filter. Likely needs the same sum() fix, but this was NOT experimentally verified in this pass (no before

**Hypothesis**: Since the non-commutative branch's degree-counting logic mirrors the commutative one, it very likely has the same bug and needs the same sum() fix, but ordering matters there (product vs combinations_with_replacement) so dedup semantics may differ. Unverified — falsify by actually running a non-commutative itermonomials(min_degrees=...) case before/after the change.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: fix-min-degree-check-total-degree

In sympy/polys/monomials.py itermonomials, in the total_degree branch (max_degrees/min_degrees given as plain ints), both the commutative and non-commutative loops filter monomials with `if max(powers.values()) >= min_degree:`. This checks the max single-variable exponent, not the total degree, so m

**Hypothesis**: The min_degree filter conflates "max single-variable exponent" with "total degree of the monomial"; replacing max(powers.values()) with the true total-degree computation (max_degree - powers[S.One]) will make itermonomials return all monomials whose real total degree is within [min_degree, max_degree], matching the documented contract "min_degree <= total_degree(monom) <= max_degree". Falsifiable 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: list-based-min-degrees-branch-is-buggy

Considered whether the list-based (Case II, min_degrees/max_degrees given as lists of per-variable bounds) branch of itermonomials (lines ~145-152) also contains a bug. Ruled out: this branch already builds power ranges per-variable independently and correctly using product() of per-variable power l

**Hypothesis**: If the list-based branch shared the same max(powers.values()) pattern it would also misbehave; refuted by reading the code, which shows it uses a structurally different, correct per-variable range construction.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: fix-max-to-sum-in-itermonomials-degree-filter

Two-line diff in sympy/polys/monomials.py itermonomials total-degree branch: change `if max(powers.values()) >= min_degree:` to `if sum(powers.values()) >= min_degree:` in both the commutative and non-commutative sub-branches. `max()` measured only the most-repeated single variable's exponent, not t

**Hypothesis**: Replacing max() with sum() in the degree filter makes itermonomials satisfy its documented contract min_degree <= total_degree(monom) <= max_degree, would be falsified if any existing test/doctest asserted the old (buggy) exclusion behavior or if sum(powers.values()) != true total degree for some item shape.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: sum-minus-powers-of-one-in-itermonomials-degree-filter

Variant fix using `sum(powers.values()) - powers[S.One] >= min_degree` instead of plain `sum(powers.values()) >= min_degree`. Algebraically identical to the plain-sum approach because powers[S.One] is structurally always 0 (the loop building `powers` explicitly does `if variable != 1: powers[variabl

**Hypothesis**: Explicitly subtracting powers[S.One] is unnecessary defensiveness; refuted as *needed* (not as *correct*) by observing that S.One's count is provably always 0 given the existing `if variable != 1` guard, so the subtraction changes no test outcome versus plain sum() while adding a redundant operation.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: restructure-per-degree-generation

Rewrite the total_degree commutative/non-commutative branches in sympy/polys/monomials.py (itermonomials, ~lines 119-144) to loop over d in range(min_degree, max_degree+1) and generate combinations_with_replacement(variables, d) / product(variables, repeat=d) per degree directly, removing the S.One 

**Hypothesis**: The bug isn't just the max()/sum() filter choice but that itermonomials pads with S.One and generates all combinations at fixed length max_degree then filters afterward — an approach that requires a filter to be correct at all. If instead the code iterates each degree d in range(min_degree, max_degree+1) and calls combinations_with_replacement(variables, d) directly on the real variables (no S.One

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Tried: stars-and-bars-exponent-tuples

Replace the commutative/non-commutative total_degree branches in itermonomials (sympy/polys/monomials.py ~119-144) with a stars-and-bars exponent-tuple generator per degree d in range(min_degree, max_degree+1), building each monomial as Mul(*(v**e for v,e in zip(variables,exps))) instead of filterin

**Hypothesis**: Rather than enumerating variable-combinations and computing degrees from them (the mechanism behind every previously tried fix, all of which patch the same powers-dict filter), total-degree monomials can be generated directly as exponent tuples via stars-and-bars: for each degree d in range(min_degree, max_degree+1), enumerate all tuples of length n=len(variables) of non-negative integers summing 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X10 — Sources consulted for degree filter itermonomials

- Manual code reading of sympy/polys/monomials.py itermonomials (lines ~121-144) plus interactive reproduction in a python REPL/worktree; confirmed against docstring contract and issue description.
- Manual code reading of sympy/polys/monomials.py itermonomials lines 145-152.
- Manual reading of sympy/polys/monomials.py lines 113-144 in current repo; contrasts with the already-tried filter-only fixes which keep the S.One-padding + single fixed-length combinations_with_replac
- Manual reading of sympy/polys/monomials.py total_degree branch (lines 113-144); considered as an alternative generation mechanism distinct from the combinations_with_replacement+filter structure all p
- Root-cause analysis of sympy/polys/monomials.py plus experimental edit-and-rerun in tmp/aspect-reproduce worktree at base commit d9b18c518d64; reverted after verifying.
- issue.md reproduction + manual code inspection of sympy/polys/monomials.py

### X11 — What has been investigated about degree filter itermonomials

Ground already covered by research on this subject.

- **root_cause_confirmation** — Confirm the exact defect: in sympy/polys/monomials.py total_degree branch, does `max(powers.values()) >= min_degree` incorrectly filter by the max single-variable exponent instead of the monomial's tr
  Looked in: sympy/polys/monomials.py itermonomials, commutative and non-commutative loops (both ~lines 121-144)
- **correct_replacement_condition** — What is the correct replacement condition, and does it need to account for the S.One padding variable (which must not count toward total degree) and work identically for both the commutative combinati
  Looked in: same function, both branches; consider using sum(powers.values()) minus any count attributed to the S.One placeholder, or filtering item before padding
- **regression_scope_list_mode** — Does the per-variable list (Case II) branch of itermonomials, and the min_degree>max_degree early-return guard, already behave correctly and require no change, so the fix should be scoped only to the 
  Looked in: sympy/polys/monomials.py lines ~145-160 (list-mode branch) and line 114-115 (min_degree>max_degree guard)

...and 2 more line(s) of ground covered.

## References

### X12 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **itermonomials_correctness_rate** (max, target 1.0).

**Established**
- fix-total-degree-check-in-itermonomials (potential)
- fix-max-to-sum-in-commutative-filter (potential)
- fix-min-degree-check-total-degree (potential)
- fix-max-to-sum-in-itermonomials-degree-filter (potential)
- sum-minus-powers-of-one-in-itermonomials-degree-filter (potential)

**Still open**
- same-sum-fix-for-noncommutative-branch (potential)
- list-based-min-degrees-branch-is-buggy (potential)
- restructure-per-degree-generation (potential)
- stars-and-bars-exponent-tuples (potential)
- aspect not yet answered: root_cause_confirmation
- aspect not yet answered: correct_replacement_condition

**Where the detail is**
- fix-total-degree-check-in-itermonomials: issue.md reproduction + manual code inspection of sympy/polys/monomials.py
- fix-max-to-sum-in-commutative-filter: Root-cause analysis of sympy/polys/monomials.py plus experimental edit-and-rerun in tmp/aspect-reproduce workt
- same-sum-fix-for-noncommutative-branch: Code inspection only (structural similarity to the confirmed commutative bug); flagged for the fix/implementat

...and 4 more line(s); see the full record.