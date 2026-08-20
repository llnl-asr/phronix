---
name: check
description: Research on check. Covers what is the exact bug in itermonomials when min_degrees is specified as an integer; how should total degree filtering work vs individual power filtering; what do existing tests reveal about expected behavior. Approaches tried: fix_max_to_sum_check, early_pruning_generation, sympy/polys/monomials.py, fix_sum_check_simplified.
subject: check
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to check |
| `X1` | References | Tried: fix_max_to_sum_check |
| `X2` | References | Tried: early_pruning_generation |
| `X3` | References | Tried: fix_sum_check_simplified |
| `X4` | References | Tried: fix_explicit_s_one_exclusion |
| `X5` | References | Sources consulted for check |







## Instructions

### I1 — How to evaluate a change to check

Figure of merit: **target_tests_passing** (max, target 1.0).

Measured by: Run hidden target tests via benchmark grading system. The tests verify that itermonomials returns all monomials with total degree between min_degrees and max_degrees when both are integers. Measure is: (passing tests) / (total tests). Command: grading system executes after patch is applied.

Cases differ along: commutative, min_degree_value, min_equals_max, num_variables.

## Rules

## References

### X1 — Tried: fix_max_to_sum_check

Change max(powers.values()) >= min_degree to check total degree: min_degree <= sum(powers.values()) <= max_degree for both commutative and non-commutative cases

**Hypothesis**: The bug is that lines 130 and 142 use max(powers.values()) >= min_degree which checks maximum individual power, not total degree. Changing to min_degree <= sum(powers.values()) <= max_degree will include all monomials whose total degree is in the specified range. This is falsifiable: if the fix is applied and tests still fail, the hypothesis about checking total degree is wrong.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: early_pruning_generation

Refactor to generate only valid-degree combinations upfront rather than generate-then-filter. Instead of using combinations_with_replacement/product to generate ALL combinations up to max_degree and then filtering, generate only combinations where min_degree <= sum(powers) <= max_degree from the sta

**Hypothesis**: The bug could be fixed by changing the combinations generation logic to only generate combinations whose total degree matches the constraints, rather than generating all combinations up to max_degree and then filtering. This would avoid generating combinations that will be filtered out.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: fix_sum_check_simplified

Replace max(powers.values()) >= min_degree with sum(powers.values()) >= min_degree only, omitting upper bound check since generation already guarantees sum <= max_degree

**Hypothesis**: The bug is that lines 130 and 142 check max(powers.values()) >= min_degree (maximum individual power) instead of total degree. Since combinations_with_replacement(variables, max_degree) generates combinations of exactly max_degree items, the sum of powers can never exceed max_degree. Therefore, we only need to check sum(powers.values()) >= min_degree. This is falsifiable: if applied and tests fail

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: fix_explicit_s_one_exclusion

Explicitly exclude S.One from degree calculations in the filter - RULED OUT by testing, S.One already handled correctly

**Hypothesis**: The issue might not be just the filter condition, but how S.One is handled in the powers dictionary. Currently the code skips S.One when incrementing (line 128: if variable != 1), but includes it in powers dict initialization (line 125). If max(powers.values()) includes S.One's count, it could cause issues. Changing the filter to explicitly exclude S.One from the check might fix it: max(p for v, p

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Sources consulted for check

- Git commit bf77d77bca (2019) by Gagandeep Singh fixed this exact bug by replacing max with sum. The fix was later lost or reverted. Documentation lines 21-26 specifies total_degree(monom) not max indi
