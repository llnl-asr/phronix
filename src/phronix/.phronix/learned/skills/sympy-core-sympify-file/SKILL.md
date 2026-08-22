---
name: sympy-core-sympify-file
description: Fix bug
subject: sympy-core-sympify-file
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix numpy float conversion |


## Instructions

### I1 — Fix numpy float conversion

Edit sympy/core/sympify.py to replace the string conversion with a.item() usage in _convert_numpy_types.

## Rules

## References
