---
name: branch-commutative
description: Research on branch commutative. Covers in the commutative branch of itermonomials (sympy/polys/monomials.py, total_degree path), does the filter `max(powers.values()) >= min_degree` use the wrong aggregation — max single-variable exponent instead of sum of exponents (total degree) — and does replacing it with `sum(powers.values()) >= min_degree` produce exactly the total-degree-bounded monomial set the docstring promises; does the non-commutative branch (product(variables, repeat=max_degree) loop) have the identical max()-vs-sum() bug, and does it need the same fix independently since it's a s
subject: branch-commutative
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to branch commutative |
| `I2` | Instructions | How to solve branch commutative |
| `X1` | References | Where research on this subject stands |
| `X3` | References | Tried: heurisch-or-multivariate_resultants-affected-by-fix |
| `X4` | References | Tried: fix_max_to_sum_in_powers_filter |
| `X5` | References | Tried: fix_by_removing_S_One_from_powers_dict |
| `X6` | References | Tried: fix_comparison_operator_direction |
| `X7` | References | Tried: total-degree-via-item-count-not-powers-sum |
| `X8` | References | Tried: fix-scope-safe-no-downstream-guards-needed-r1 |
| `X9` | References | Tried: fix-both-branches-max-to-sum-r1 |
| `X10` | References | Tried: fix-via-Mul-total-degree-helper |
| `X11` | References | Sources consulted for branch commutative |










































































































































































































## Instructions

### I1 — How to evaluate a change to branch commutative

Figure of merit: **correct_monomial_set_rate** (max, target 1.0).

Measured by: For each corpus instance, call itermonomials(variables, max_degrees, min_degrees) with the given args, collect the returned set of monomials, and compare (as a Python set, order-independent) against the expected set computed independently (e.g. via total_degree/per-variable-degree filtering over all combinations_with_replacement / product tuples up to max_degrees). Score = (# instances whose retur

Cases differ along: commutativity, degree_mode, min_max_relation, n_variables.

### I2 — How to solve branch commutative

Try these in order, ONE at a time. Ranked by measured **correct_monomial_set_rate** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A8` **fix-scope-safe-no-downstream-guards-needed-r1** — correct_monomial_set_rate unmeasured, potential — Fixing the min_degrees list-filtering bug in itermonomials is safe: no in-repo caller pass
2. `A9` **fix-both-branches-max-to-sum-r1** — correct_monomial_set_rate unmeasured, potential — In sympy/polys/monomials.py itermonomials(), total_degree branch: change `if max(powers.va
3. `A3` **heurisch-or-multivariate_resultants-affected-by-fix** — correct_monomial_set_rate unmeasured, potential — REFUTED: hypothesis that sympy/integrals/heurisch.py or sympy/polys/multivariate_resultant

...and 5 lower-ranked approach(es); see `research_rank`.## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **correct_monomial_set_rate** (max, target 1.0).

**Established**
- heurisch-or-multivariate_resultants-affected-by-fix (potential)
- fix_max_to_sum_in_powers_filter (potential)

**Still open**
- fix_by_removing_S_One_from_powers_dict (potential)
- fix_comparison_operator_direction (potential)
- sympy/polys/monomials.py (potential correct_monomial_set_rate=0.0)
- total-degree-via-item-count-not-powers-sum (potential)
- fix-both-branches-max-to-sum-r1 (potential)
- fix-via-Mul-total-degree-helper (potential)

**Ruled out**
- fix-scope-safe-no-downstream-guards-needed (failed correct_monomial_set_rate=1.0) — try 1: target tests still failing: test_monomials
- fix-both-branches-max-to-sum (failed correct_monomial_set_rate=1.0) — try 2: target tests still failing: test_monomials
- fix-scope-safe-no-downstream-guards-needed-r1 (failed) — try 3: target tests still failing: test_monomials

**Where the detail is**
- fix-scope-safe-no-downstream-guards-needed: tmp/research/aspect-downstream-impact.md; grep -rn "itermonomials(" --include=*.py sympy
- heurisch-or-multivariate_resultants-affected-by-fix: tmp/research/aspect-downstream-impact.md, lines 6-23

...and 5 more line(s); see the full record.### X2 — What has been investigated about branch commutative

Ground already covered by research on this subject.

- **root_cause_commutative_branch** — In the commutative branch of itermonomials (sympy/polys/monomials.py, total_degree path), does the filter `max(powers.values()) >= min_degree` use the wrong aggregation — max single-variable exponent 
  Looked in: sympy/polys/monomials.py itermonomials(), commutative combinations_with_replacement loop
- **non_commutative_branch_same_bug** — Does the non-commutative branch (product(variables, repeat=max_degree) loop) have the identical max()-vs-sum() bug, and does it need the same fix independently since it's a separate code path with dup
  Looked in: sympy/polys/monomials.py itermonomials(), non-commutative product loop
- **downstream_impact** — Which other sympy functions or tests call itermonomials with an explicit min_degrees (e.g. polynomial ring / PDE / physics.mechanics modules), and could correcting the filter change monomial counts/or
  Looked in: repo-wide grep for itermonomials( usages and sympy/polys/tests/test_monomials.py

### X3 — Tried: heurisch-or-multivariate_resultants-affected-by-fix

REFUTED: hypothesis that sympy/integrals/heurisch.py or sympy/polys/multivariate_resultants.py would be affected by a min_degrees filter fix, since they call itermonomials.

**Hypothesis**: These two modules call itermonomials, so they might rely on (or be broken by a change to) min_degrees filtering behavior.

**Status**: potential (train 0/1). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: fix_max_to_sum_in_powers_filter

Replace `max(powers.values()) >= min_degree` with `sum(powers.values()) >= min_degree` in both the commutative and non-commutative branches of itermonomials() total_degree path in sympy/polys/monomials.py. Empirically verified this produces the correct full set of monomials (e.g. x*y now included fo

**Hypothesis**: powers[S.One] is always 0 (never incremented due to `if variable != 1` guard), so sum(powers.values()) equals the true total degree of the monomial (sum of exponents over real variables only), while max(powers.values()) is just the largest single-variable exponent — not total degree. Since max_degree is enforced correctly by construction (item always has exactly max_degree factors), only the min_d

**Status**: potential (train 1/1). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: fix_by_removing_S_One_from_powers_dict

REFUTED as unnecessary. Initial hypothesis was that S.One padding pollutes the powers dict/max or sum computation and must be explicitly excluded. Direct inspection showed powers[S.One] is always initialized to 0 and never incremented (the loop only does `powers[variable] += 1` when `variable != 1`)

**Hypothesis**: Ruled out: thought S.One's count needed explicit subtraction from sum(powers.values()) to get true total degree, i.e. fix would need to be `sum(powers.values()) - powers[S.One]` or similar. Refuted by observing powers[S.One] is structurally always 0, so plain sum(powers.values()) already equals true total degree with no extra correction.

**Status**: potential (train 0/1). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: fix_comparison_operator_direction

REFUTED. Considered whether the bug was in the comparison direction/operator (e.g. should be <= instead of >=, or bound should be checked differently) rather than in the aggregation function. Ruled out: the `>= min_degree` comparison is semantically correct once given the right aggregate; the max_de

**Hypothesis**: Ruled out: hypothesized the filter condition's comparison operator or bound logic was the defect. Refuted because swapping only the aggregation (max->sum) while keeping `>= min_degree` unchanged fully fixes the output against the docstring contract.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: total-degree-via-item-count-not-powers-sum

Alternate implementation of the same root-cause fix in sympy/polys/monomials.py itermonomials(), total_degree branch (lines 113-144). Instead of building a powers dict and comparing sum(powers.values()) >= min_degree (the primary approach, fix-both-branches-max-to-sum), compute the true total degree

**Hypothesis**: If total degree is computed as max_degree - item.count(S.One) instead of sum(powers.values()), the result is arithmetically identical to the sum-based fix (since sum(powers.values()) == max_degree - count of S.One entries in item), so it should produce the same corrected output for itermonomials([x1,x2,x3], 3, min_degrees=3) — namely including mixed monomials like x1*x2**2. Refuted if this differs

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: fix-scope-safe-no-downstream-guards-needed-r1

Fixing the min_degrees list-filtering bug in itermonomials is safe: no in-repo caller passes an explicit non-default min_degrees, so no guard/compat shim is needed beyond the function itself.

Revision 1: Same code change (max(powers.values()) -> sum(powers.values()) in both the commutative and non-

**Hypothesis**: Same code change (max(powers.values()) -> sum(powers.values()) in both the commutative and non-commutative total_degree branches of itermonomials in sympy/polys/monomials.py), but the executing step must invoke the test via `python -m pytest` or sympy's own test runner (`bin/test` / `python -c "import sympy; sympy.test('sympy/polys/tests/test_monomials.py')"`) after confirming pytest is installed 

**Status**: potential (train 6/6, validate 3/3). Investigated already — extend this rather than re-deriving it.

### X9 — Tried: fix-both-branches-max-to-sum-r1

In sympy/polys/monomials.py itermonomials(), total_degree branch: change `if max(powers.values()) >= min_degree:` to `if sum(powers.values()) >= min_degree:` at both line 130 (commutative branch, monomials_list_comm) and line 142 (non-commutative branch, monomials_list_non_comm). powers[S.One] is ne

**Hypothesis**: If itermonomials' total_degree filter uses sum(powers.values()) instead of max(powers.values()), then itermonomials(states,3,min_degrees=3) will include all total-degree-3 monomials (not just pure powers), matching the docstring and the issue's expected output; this is falsified only if the actual test run (with a working pytest) still fails after the edit.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X10 — Tried: fix-via-Mul-total-degree-helper

In sympy/polys/monomials.py itermonomials(), commutative and non-commutative total_degree branches: instead of hand-building a `powers` dict per item and comparing max/sum, compute the monomial degree directly as `len(item) - item.count(S.One)` (equivalent to counting non-unit factors in the combina

**Hypothesis**: total_degree of a monomial built from a length-max_degree tuple of variables+[S.One] equals the count of non-S.One entries in that tuple, so `len(item) - item.count(S.One)` is arithmetically identical to `sum(powers.values())` but avoids constructing/maintaining the powers dict for the filter path, reducing surface area for a mis-aggregation bug. Falsified if this count ever diverges from sum(powe

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X11 — Sources consulted for branch commutative

- Issue sympy/sympy#21837 (itermonomials min_degrees bug); sympy/polys/monomials.py current checkout lines 113-144
