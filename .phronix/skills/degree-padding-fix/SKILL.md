---
name: degree-padding-fix
description: Fixes issue #24066 by restoring correct monomials implementation
subject: degree-padding-fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix corrupted monomials.py |


## Instructions

### I1 — Fix corrupted monomials.py

Replace sympy/polys/monomials.py with the upstream version from sympy v1.12 to correct the corrupted docstring and ensure the total_degree filter uses sum(powers.values()) >= min_degree. This restores correct behavior of itermonomials.

## Rules

## References
