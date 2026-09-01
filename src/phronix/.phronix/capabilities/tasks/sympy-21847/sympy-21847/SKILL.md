---
name: sympy-21847
description: Fixes itermonomials to correctly respect min_degrees by checking total degree.
subject: sympy-21847
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix itermonomials min_degrees handling |


## Instructions

### I1 — Fix itermonomials min_degrees handling

In `sympy/polys/monomials.py` replace the condition checking `min_degree`.

Change the lines:
```python
-                if max(powers.values()) >= min_degree:
+                if sum(powers.values()) >= min_degree:
```
for both the commutative and non‑commutative monomial generation sections. This ensures the filter uses total degree (sum of exponents) as required by the `min_degrees` argument.

## Rules

## References
