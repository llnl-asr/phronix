---
name: sympy-24066-fix-exp-dimensionless
description: The sympy-24066-fix-exp-dimensionless subject.
subject: sympy-24066-fix-exp-dimensionless
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Observe failing test |


## Instructions

### I1 — Observe failing test

Run `probe_run_pylint_check` with test selection `sympy/physics/units/tests/test_quantities.py -k exp` to see the ValueError indicating exp handling is incorrect.

## Rules

## References
