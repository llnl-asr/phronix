---
name: sympy-sympy-14308
description: Solution for sympy issue 12675
subject: sympy-sympy-14308
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix LaTeX sequence rendering |


## Instructions

### I1 — Fix LaTeX sequence rendering

Update `_print_SeqFormula` in `sympy/printing/latex.py` to return a LaTeX string using `\left[ ... \right]` brackets instead of plain brackets. Ensure slice handling returns a list. The corrected return statement should be:
```
return r"\left[" + r", ".join(self._print(el) for el in printset) + r"\right]"
```
Also keep the earlier adjustments for slice conversion to list.

## Rules

## References
