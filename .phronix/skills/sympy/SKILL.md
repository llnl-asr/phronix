---
name: sympy
description: Research on sympy. Covers what is the exact bug in itermonomials when min_degrees is specified as an integer; how should total degree filtering work vs individual power filtering; what do existing tests reveal about expected behavior. Approaches tried: fix_max_to_sum_check, early_pruning_generation.
subject: sympy
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to sympy |
| `I2` | Instructions | How to solve sympy |
| `I3` | Instructions | Fix test environment before applying code fixes |
| `R1` | Rules | Verify pytest is installed before claiming task completion |
| `R2` | Rules | Search for environment rules before applying any fix |
| `X1` | References | Tried: fix_max_to_sum_check |
| `X2` | References | Tried: early_pruning_generation |
| `X3` | References | Sources consulted for sympy |
| `X4` | References | What has been investigated about sympy |










## Instructions

### I1 — How to evaluate a change to sympy

Figure of merit: **target_tests_passing** (max, target 1.0).

Measured by: Run hidden target tests via benchmark grading system. The tests verify that itermonomials returns all monomials with total degree between min_degrees and max_degrees when both are integers. Measure is: (passing tests) / (total tests). Command: grading system executes after patch is applied.

Cases differ along: commutative, min_degree_value, min_equals_max, num_variables.

### I2 — How to solve sympy

Try these in order. Ranked by measured **target_tests_passing** (max, target 1.0). Each one's hypothesis and evidence is in the matching `Tried:` reference on this skill.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. **fix_max_to_sum_check** — target_tests_passing 1.000, potential — Change max(powers.values()) >= min_degree to check total degree: min_degree <= sum(powers.values()) <= max_deg
2. **early_pruning_generation** — target_tests_passing 0.800, potential — Refactor to generate only valid-degree combinations upfront rather than generate-then-filter

### I3 — Fix test environment before applying code fixes

When test execution fails with environment errors (missing modules, wrong Python version, missing dependencies), fix the environment before applying code changes. Install missing dependencies, activate the right environment, or document what cannot be fixed. Never apply a code fix without being able to test it. If tests cannot run, state explicitly: "Applied fix but cannot verify - test environment broken: [exact error]". A fix without verification is a hypothesis, not a solution.

## Rules

### R1 — Verify pytest is installed before claiming task completion

Before reporting a sympy fix as complete, verify pytest is installed and can import. The testbed at `/opt/miniconda3/envs/testbed` may be missing pytest, causing all tests to fail with "No module named pytest" even when the fix is correct. Run `python -c "import pytest"` first. If it fails, install with `pip install pytest` before running tests. Without this, correct fixes appear identical to broken fixes in grading output.

### R2 — Search for environment rules before applying any fix

When working on sympy tasks, search for BOTH the fix AND environment setup before starting. Use two queries: one for the bug itself (e.g., "itermonomials min_degrees") AND one for environment setup (e.g., "sympy pytest environment testbed"). If you only search for the bug, you'll retrieve the fix (L1) but miss the required environment setup (R1, I3), apply a correct fix to a broken environment, and fail grading. This has happened on multiple attempts for task 21847.

## References

### X1 — Tried: fix_max_to_sum_check

Change max(powers.values()) >= min_degree to check total degree: min_degree <= sum(powers.values()) <= max_degree for both commutative and non-commutative cases

**Hypothesis**: The bug is that lines 130 and 142 use max(powers.values()) >= min_degree which checks maximum individual power, not total degree. Changing to min_degree <= sum(powers.values()) <= max_degree will include all monomials whose total degree is in the specified range. This is falsifiable: if the fix is applied and tests still fail, the hypothesis about checking total degree is wrong.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: early_pruning_generation

Refactor to generate only valid-degree combinations upfront rather than generate-then-filter

**Hypothesis**: The bug could be fixed by changing the combinations generation logic to only generate combinations whose total degree matches the constraints, rather than generating all combinations up to max_degree and then filtering. This would check: when generating combinations, track running total and prune branches early. This is falsifiable: if implemented and tests fail, the hypothesis about early pruning

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Sources consulted for sympy

- Git commit bf77d77bca (2019) by Gagandeep Singh fixed this exact bug by replacing max with sum. The fix was later lost or reverted. Documentation lines 21-26 specifies total_degree(monom) not max indi

### X4 — What has been investigated about sympy

Ground already covered by research on this subject.

- **root_cause_analysis** — What is the exact bug in itermonomials when min_degrees is specified as an integer?
  Looked in: sympy/polys/monomials.py lines 113-144, the total_degree=True branch
- **degree_filtering_logic** — How should total degree filtering work vs individual power filtering?
  Looked in: Mathematical definition of total degree, documentation at lines 21-26
- **existing_tests** — What do existing tests reveal about expected behavior?
  Looked in: sympy/polys/tests/test_monomials.py
