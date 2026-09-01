---
name: sympy-sympy-18698
description: The sympy-sympy-18698 subject.
subject: sympy-sympy-18698
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis for sympy issue 18698 - root cause |
| `R1` | Rules | Do not merge coprime factors by multiplicity alone |



## Instructions

### I1 — Diagnosis for sympy issue 18698 - root cause

The dmp_sqf_list function in sympy/polys/sqfreetools.py incorrectly merges coprime factors with identical multiplicities. For input (x^2+1)*(x-1)^2*(x-2)^3*(x-3)^3, expected output is [(x^2+1,1),(x-1,2),(x-3,3),(x-2,3)] but current output wrongly combines (x-2) and (x-3) into (x^2-5x+6,3). The GCD-based dmp_inner_gcd cannot distinguish coprime factors sharing the same multiplicity pattern.

## Rules

### R1 — Do not merge coprime factors by multiplicity alone

Never combine distinct irreducible factors into a single factor just because they share the same multiplicity. The square-free part must preserve each distinct factor separately, even when multiplicities match.

## References
