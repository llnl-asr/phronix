---
name: degree-filter-padding
description: Research on degree filter padding. Covers what is the correct condition for min_degrees in itermonomials; how does the padding variable S.One affect the min_degrees logic. Approaches tried: explicit degree loop no padding, fix sum not max degree filter.
subject: degree-filter-padding
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to degree filter padding |
| `X1` | References | Tried: explicit-degree-loop-no-padding |
| `X2` | References | Tried: fix-sum-not-max-degree-filter |
| `X3` | References | Where research on this subject stands |

























## Instructions

### I1 — How to evaluate a change to degree filter padding

Figure of merit: **itermonomials_correctness_rate** (max, target 1.0).

Measured by: fraction of correctly generated monomials

Cases differ along: example.

## Rules

## References

### X1 — Tried: explicit-degree-loop-no-padding

Rewrite total_degree branch to iterate over total degree and generate monomials explicitly

**Hypothesis**: Using explicit loops over total degree ensures correct monomial generation for min_degrees integer case

**Status**: potential (train 0/1). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: fix-sum-not-max-degree-filter

Replace max(powers.values()) with sum(powers.values()) in integer min_degrees case

**Hypothesis**: Changing condition to sum(powers.values()) >= min_degree correctly filters monomials by total degree

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **itermonomials_correctness_rate** (max, target 1.0).

**Still open**
- imp.py, sympy/polys/monomials.py (potential itermonomials_correctness_rate=0.0)
- sitecustomize.py (potential itermonomials_correctness_rate=0.0)
- aspect not yet answered: filter_condition
- aspect not yet answered: padding_variable

**Ruled out**
- explicit-degree-loop-no-padding (failed) — try 1: target tests still failing: test_monomials
- fix-sum-not-max-degree-filter (failed) — try 1: target tests still failing: tests/test_blueprints.py::test_dotted_name_not_allowed,

**Where the detail is**
- explicit-degree-loop-no-padding: sympy/polys/monomials.py
- fix-sum-not-max-degree-filter: sympy/polys/monomials.py
- imp.py, sympy/polys/monomials.py: benchmark attempt
- sitecustomize.py: benchmark attempt
- full record: research topic `sympy__sympy-21847` (via research_status, only if this summary is not enough)