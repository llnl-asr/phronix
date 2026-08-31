---
name: sympy-sympy-22840
description: The sympy-derivative-kind subject.
subject: sympy-sympy-22840
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I1 Problem Statement |
| `I2` | Instructions | I7 Naming |



## Instructions

### I1 — I1 Problem Statement

Fix cse() behavior for MatrixSymbol substitution. When MatrixSymbol objects are passed to cse, they are not correctly substituted, causing test failures in `test_cse_MatrixSymbol` and `test_multidim_c_argument_cse`.

### I2 — I7 Naming

Use clear, descriptive names for new functions and variables, e.g., `sub_in_matrixsymbols` for substituting MatrixSymbol objects, and `t44` for generating 4x4 matrices of symbols.

## Rules

## References

- `skill_load(name="sympy-derivative-kind", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

