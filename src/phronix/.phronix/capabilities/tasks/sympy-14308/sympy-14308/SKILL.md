---
name: sympy-14308
description: Fix vector pretty printing alignment and baseline centering in SymPy.
subject: sympy-14308
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem Description |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Instructions |
| `I4` | Instructions | Constraints |
| `I5` | Instructions | Pitfalls |

## Instructions

### I1 — Problem Description

Vectors mis‑aligned in pretty printing, causing failing tests `test_issue_12675` and `test_pretty_print_unicode` (baseline centering also incorrect).

### I2 — Key Idea

Adjust the pretty‑printing layout logic for vectors to correctly center the baseline and include the basis label.

### I3 — Instructions

1. Open `sympy/printing/pretty/pretty.py`.
2. Locate the `_print_BasisDependent` method handling vector basis.
3. Modify the string composition to place the basis label (`e_j`) after the pretty‑printed expression and ensure the baseline is centered using appropriate padding.
4. Run the target tests `test_issue_12675` and `test_pretty_print_unicode` and confirm they pass.
5. Ensure all regression tests remain green.

### I4 — Constraints

Do not change import statements unrelated to printing. Preserve existing functionality for other types. The changes must not break ASCII pretty printing of BasisDependent objects.
Maintain compatibility with Python 3.8+ and existing sympy API.

### I5 — Pitfalls

Avoid moving the basis label before the expression, as this re‑introduces mis‑alignment.
Do not alter the baseline calculation logic elsewhere, which could affect other pretty‑printed structures.
Be careful not to introduce new imports that could cause circular dependencies.

## Rules
