---
name: sympy-sympy-11897
description: Fix Mathematica code printer to preserve argument order for Max and similar non-listable functions
subject: sympy-sympy-11897
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | understand-max-ordering |
| `I2` | Instructions | fix-mcode-function-printing |
| `I3` | Instructions | verify-fix |
| `I4` | Instructions | final-verification-steps |
| `R1` | Rules | preserve-argument-order |


## Instructions

### I1 — understand-max-ordering

In sympy, Max(x, 2) has args (x, 2) but mathematica_code outputs Max(2, x) - arguments are reversed. The MCodePrinter._print_Function method at mathematica.py:96-102 needs to handle functions like Max that may have non-obvious argument ordering when converting to Mathematica format.

### I2 — fix-mcode-function-printing

Modify MCodePrinter._print_Function in sympy/printing/mathematica.py to preserve argument order for functions that are not in known_functions. The current fallback at line 102 prints args in whatever order sympy stores them, but Mathematica expects the original order. Add special handling for Max (and similar functions like Min) to ensure args are printed in the order they appear in the expression, not reversed or sorted.

### I3 — verify-fix

Test that mathematica_code(Max(x, 2)) produces 'Max[x, 2]' and mathematica_code(Max(2, x)) produces 'Max[x, 2]' - both should preserve the input argument order. Also verify existing tests still pass: test_Integer, test_Rational, test_Function, test_Pow, test_Mul, test_constants, test_containers, test_Integral, test_Derivative, test_Sum.

### I4 — final-verification-steps

FINAL VERIFICATION: After applying the fix to mathematica.py, run these tests in order to confirm the fix works and nothing is broken:
1. `python3 -c "from sympy import mathematica_code as mcode; from sympy import symbols; x = symbols('x'); print('Max(x, 2):', repr(mcode(Max(x, 2))))"`
2. `python3 -c "from sympy import mathematica_code as mcode; from sympy import symbols; x = symbols('x'); print('Max(2, x):', repr(mcode(Max(2, x))))"`
3. `python3 -c "from sympy import mathematica_code as mcode; from sympy import symbols; x,y = symbols('x y'); print('Max(x, y):', repr(mcode(Max(x, y))))"`
4. Run the full test suite: `python3 -m pytest sympy/printing/tests/test_mathematica.py -v`
5. Verify test_Mathematica_1 and test_Mathematica_2 (if they exist) still pass.
All tests must show Max[x, 2] (or Max[x, y] etc.) with preserved argument order, not Max(2, x) or any reversed form.

## Rules

### R1 — preserve-argument-order

When printing a Function to Mathematica code, always preserve the original argument order from the sympy expression. Do not sort, reverse, or reorder args unless the function's mathematical semantics require it (which is rare for code printing). The stringify method should output args in the same order as expr.args.

## References

- `skill_load(name="fix-mcode-max-order", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
