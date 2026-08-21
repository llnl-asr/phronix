---
name: sympy
description: Research on sympy.
subject: sympy
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to sympy |
| `X1` | References | Where research on this subject stands |






## Instructions

### I1 — How to evaluate a change to sympy

Figure of merit: **itermonomials_correctness_rate** (max, target 1.0).

Measured by: For each corpus instance, call sp.itermonomials(variables, max_degrees, min_degrees=min_degrees) (integer or list form per instance) and collect the resulting set of monomials. Compute the expected set independently: for the integer (total-degree) form, all monomials over `variables` with min_degree <= total_degree <= max_degree, generated via combinations_with_replacement(variables, d) for d in r

Cases differ along: case_type, commutativity, degree_form, min_max_relation, num_variables.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **itermonomials_correctness_rate** (max, target 1.0).

**Still open**
- aspect not yet answered: fix_scope_verification
- aspect not yet answered: padding_variable_interaction
- aspect not yet answered: existing_test_and_doctest_compatibility
- aspect not yet answered: list_form_branch_isolation