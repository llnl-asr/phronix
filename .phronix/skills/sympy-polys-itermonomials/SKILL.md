---
name: sympy-polys-itermonomials
description: The sympy-polys-itermonomials subject.
subject: sympy-polys-itermonomials
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Validate min_degrees bounds |


## Instructions

## Rules

### R1 — Validate min_degrees bounds

If any entry in `min_degrees` is negative or greater than the corresponding entry in `max_degrees`, raise a `ValueError` with an appropriate message. This prevents silent generation of incorrect monomials.

## References
