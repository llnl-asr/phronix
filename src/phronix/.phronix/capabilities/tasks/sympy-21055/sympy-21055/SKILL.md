---
name: sympy-21055
description: The sympy-21055 subject.
subject: sympy-21055
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem: refine() does not simplify integral with sin and exponential under positive assumption |


## Instructions

### I1 — Problem: refine() does not simplify integral with sin and exponential under positive assumption

The issue occurs when calling `refine(Integral(sin(x)*exp(-a*x), (x,0,oo)), Q.positive(a))` which should simplify to `1/(a**2 + 1)` but does not because `sin` lacks refinement support.

## Rules

## References
