---
name: sympy-sympy-15011
description: The sympy-sympy-15011 subject.
subject: sympy-sympy-15011
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Naming convention for this skill |
| `I3` | Instructions | Fix lambdify dummify with MatrixSymbol curly names |

## Instructions

### I1 — Problem

Lambdify fails when a MatrixSymbol name contains curly braces, causing a SyntaxError during lambda generation.

### I2 — Naming convention for this skill

Use the short name "sympy-sympy-15011" which matches the task identifier, and reference it by this name in future attempts.

### I3 — Fix lambdify dummify with MatrixSymbol curly names

Problem: lambdify with dummify=True generates invalid Python code when using MatrixSymbol with curly brace names (e.g., {v}). The generated function signature has `def _lambdifygenerated({v}):` which is not valid Python syntax.

Root cause: In sympy/utilities/lambdify.py _preprocess method, the isinstance check only tested `isinstance(arg, Symbol)`. MatrixSymbol is NOT a subclass of Symbol — it's a separate class — so MatrixSymbol instances bypassed the dummify check entirely and were just stringified, preserving the curly brace name in the generated code.

Fix: Two changes to sympy/utilities/lambdify.py:

1. Line 509: Added MatrixSymbol to the import from sympy.matrices
2. Line 518: Changed `isinstance(arg, Symbol)` to `isinstance(arg, (Symbol, MatrixSymbol))` so MatrixSymbol objects with non-identifier names get properly dummified, generating valid Python signatures like `def _lambdifygenerated(_Dummy_N):` instead of `def _lambdifygenerated({v}):`.

## References
