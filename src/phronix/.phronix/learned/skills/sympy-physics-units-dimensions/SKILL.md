---
name: sympy-physics-units-dimensions
description: The sympy-physics-units-dimensions subject.
subject: sympy-physics-units-dimensions
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Validate exponent dimension in _collect_factor_and_dimension |


## Instructions

## Rules

### R1 — Validate exponent dimension in _collect_factor_and_dimension

Before computing the factor for a Power node, call `self.get_dimension_system().is_dimensionless(exp_dim)`. If it returns false, raise `ValueError` indicating the exponent must be dimensionless. This prevents returning a non‑dimensionless result for expressions like `exp(T/(C*R))`.

## References
