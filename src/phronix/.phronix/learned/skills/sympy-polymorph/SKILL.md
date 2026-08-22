---
name: sympy-polymorph
description: The sympy-polymorph subject.
subject: sympy-polymorph
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Avoid unrelated code changes when fixing itermonomials |


## Instructions

## Rules

### R1 — Avoid unrelated code changes when fixing itermonomials

When fixing the total-degree bug in `sympy/polys/monomials.py`, do not modify other files or add unrelated functionality. Focus solely on replacing the `max(powers.values())` check with `sum(powers.values())` to correct the total-degree calculation.

## References
