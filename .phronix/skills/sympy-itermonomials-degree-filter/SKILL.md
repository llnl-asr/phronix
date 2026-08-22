---
name: sympy-itermonomials-degree-filter
description: The sympy-itermonomials-degree-filter subject.
subject: sympy-itermonomials-degree-filter
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Use total degree (sum of powers) for filter |


## Instructions

## Rules

### R1 — Use total degree (sum of powers) for filter

Replace `if max(powers.values()) >= min_degree` with `if sum(powers.values()) >= min_degree` to correctly filter by total degree.

## References
