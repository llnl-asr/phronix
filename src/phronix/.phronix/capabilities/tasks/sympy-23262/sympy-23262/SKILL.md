---
name: sympy-23262
description: Fix Python code printer tuple single-element comma issue in SymPy 1.10
subject: sympy-23262
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify the printer file |
| `I2` | Instructions | Modify tuple handling |
| `I3` | Instructions | Run the failing test |
| `I4` | Instructions | Run full test suite |
| `R1` | Rules | Do not alter other printer behavior |
| `R2` | Rules | Maintain PEP8 style |

## Instructions

### I1 — Identify the printer file

Open `sympy/printing/pycode.py` and locate the function handling tuple literals for code generation.

### I2 — Modify tuple handling

In the code that outputs tuple literals, add a check: if the tuple length is 1, ensure the generated string ends with a trailing comma, e.g., `return f'({elem},)'`.

### I3 — Run the failing test

Execute the test `sympy/printing/tests/test_pycodeprinter.py::test_lambdify_tuple_one_element` to verify the fix passes.

### I4 — Run full test suite

Run the project's test suite to ensure no regressions are introduced.

## Rules

### R1 — Do not alter other printer behavior

Ensure changes only affect the single‑element tuple case; all other tuple outputs must remain unchanged.

### R2 — Maintain PEP8 style

The modified code must conform to the project's PEP8 formatting rules.
