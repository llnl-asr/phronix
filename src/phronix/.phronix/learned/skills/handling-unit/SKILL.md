---
name: handling-unit
description: Research on handling unit. Covers does SI._collect_factor_and_dimension correctly identify dimensionless exponents in unit expressions; does the fix handle nested exp calls within arithmetic expressions; are negative power units correctly treated as dimensionless after exponentiation. Approaches tried: (no files changed).
subject: handling-unit
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to handling unit |
| `X1` | References | Where research on this subject stands |









## Instructions

### I1 — How to evaluate a change to handling unit

Figure of merit: **fix-dimensionless-exponent** (max, target 1.0).

Measured by: count of hidden target tests passing after applying fix

Cases differ along: expression_type, unit_complexity.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **fix-dimensionless-exponent** (max, target 1.0).

**Still open**
- (no files changed) (potential)
- aspect not yet answered: dimensionless_exponent_detection
- aspect not yet answered: nested_exp_handling
- aspect not yet answered: negative_power_units
- aspect not yet answered: sqrt_unit_handling
- aspect not yet answered: complex_unit_products

**Where the detail is**
- (no files changed): benchmark attempt
- full record: research topic `sympy__sympy-24066` (via research_status, only if this summary is not enough)