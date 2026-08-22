---
name: sympy-sympy-21847
description: Rule for itermonomials total-degree behavior
subject: sympy-sympy-21847
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Correct total-degree filtering for itermonomials |
| `R2` | Rules | Reject max-exponent filter for itermonomials |



## Instructions

## Rules

### R1 — Correct total-degree filtering for itermonomials

The itermonomials function must filter monomials based on total degree, not on the maximum exponent of any variable. When min_degrees is set, include all monomials whose sum of exponents >= min_degrees, even if each individual exponent is lower.

### R2 — Reject max-exponent filter for itermonomials

The approach of filtering monomials using max(powers.values()) >= min_degree is incorrect; it excludes valid monomials where total degree meets the requirement but individual exponents are lower.

## References
