---
name: sympy-15345
description: Fix Mathematica printing of Max to preserve argument order for SymPy expressions.
subject: sympy-15345
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Modify _print_Function in mathematica.py to handle Max specially |
| `R1` | Rules | Do not alter handling of other functions |
| `R2` | Rules | Preserve existing test expectations for Min and other functions |

## Instructions

### I1 — Modify _print_Function in mathematica.py to handle Max specially

In file sympy/printing/mathematica.py, locate the _print_Function method. Add a conditional for expr.func.__name__ == "Max". Extract args, reorder by moving Symbol instances before others, then return "Max[%s]" % self.stringify(ordered, ", ")

## Rules

### R1 — Do not alter handling of other functions

All other function printing should remain unchanged; only Max receives special handling.

### R2 — Preserve existing test expectations for Min and other functions

The change must not affect existing Min output or other tests.
