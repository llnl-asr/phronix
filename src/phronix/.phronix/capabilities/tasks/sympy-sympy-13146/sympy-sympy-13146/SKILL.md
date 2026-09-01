---
name: sympy-sympy-13146
description: The sympy-mathematica-printer-fix subject.
subject: sympy-sympy-13146
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | _print_Float formatting fix |


## Instructions

## Rules

### R1 — _print_Float formatting fix

Fix _print_Float to use '{:g}' format which strips trailing zeros and uses 'e' for scientific notation, then replace 'e' with Mathematica *^ notation.
Original '{:.15g}' format produced trailing zeros (e.g., '3.50000000000000') and the 'e' replacement didn't activate for numbers like 3.5 that don't use e-notation.

## References
