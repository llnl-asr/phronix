---
name: sympy-19254
description: What is known about sympy-19254: I7 Identify failing bound reduction, I9 Restore original exponent in Mignotte bounds, R1 Preserve regression suite
subject: sympy-19254
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7 Identify failing bound reduction |
| `I2` | Instructions | I9 Restore original exponent in Mignotte bounds |
| `R1` | Rules | R1 Preserve regression suite |

## Instructions

### I1 — I7 Identify failing bound reduction

The failing tests stem from reducing the exponent in the Mignotte bound functions from `2**n` to `2**(n-1)`. This caused `dup_zz_mignotte_bound` to return 16 instead of expected 6, and similar regressions in related functions.

### I2 — I9 Restore original exponent in Mignotte bounds

Edit `sympy/polys/factortools.py`:
- In `dup_zz_mignotte_bound`, change the return line back to `return K.sqrt(K(n + 1))*2**n*a*b`.
- In `dmp_zz_mignotte_bound`, similarly revert to `return K.sqrt(K(n + 1))*2**n*a*b`.
Run the test suite to ensure `test_dup_zz_mignotte_bound` expects 6 and `test_dmp_zz_mignotte_bound` expects 32, and that no regressions appear.

## Rules

### R1 — R1 Preserve regression suite

All existing tests (16 of 18) must continue to pass after changes. Do not modify any other function affecting them.
