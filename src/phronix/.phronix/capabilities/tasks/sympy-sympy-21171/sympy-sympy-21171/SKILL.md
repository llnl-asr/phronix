---
name: sympy-sympy-21171
description: The sympy-sympy-21171 subject.
subject: sympy-sympy-21171
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis for sympy task 21171 |
| `I2` | Instructions | _print_SingularityFunction exp parameter fix |
| `R1` | Rules | _print_SingularityFunction exp parameter |




## Instructions

### I1 — Diagnosis for sympy task 21171

Task 254-sympy__sympy-21171: Investigation of SingularityFunction LaTeX printing in sympy/printing/latex.py

Key findings:
- Modified file: sympy/printing/latex.py (git status shows M sympy/printing/latex.py)
- Function _print_SingularityFunction exists at line 1-7 of sympy/printing/latex.py
- The function prints SingularityFunction objects in LaTeX format using the pattern: {\left\langle shift \right\rangle}^{power}
- Research framework tracking: This task uses the phronix research framework with exact naming convention "sympy-sympy-21171" for future lookups
- The diagnosis was not written during the previous session attempt, hence this filing

Context from earlier investigation:
- Git repository: $SCRATCH_ROOT/phronix-bench/runs/claude-0829-040235/claude-phronix/tasks/254-sympy__sympy-21171/attempt-2/repo
- Research files referenced but research-2.md not found at expected path
- Multiple memory/cache files exist in the task directory
- User instruction: "If the diagnosis is incomplete, write what you have. A partial fix the next attempt can build on is worth more than a complete one it never sees."

Note: This diagnosis is filed under the exact name "sympy-sympy-21171" as instructed. The next attempt will look up by this exact name and by nothing else. This is a partial diagnosis capturing what was available from context without re-reading source files.

### I2 — _print_SingularityFunction exp parameter fix

When _print_Pow encounters a Pow expression where the base is a Function (like SingularityFunction), it passes an exp keyword argument. _print_SingularityFunction only accepted expr — not exp, causing TypeError.

Fix: Add exp=None parameter to _print_SingularityFunction in sympy/printing/latex.py. When exp is not None, append it to the power notation: power = r"%s^{%s}" % (power, exp). The exp parameter defaults to None, preserving original behavior when not called with an exponent.

File: sympy/printing/latex.py, function _print_SingularityFunction.

## Rules

### R1 — _print_SingularityFunction exp parameter

The _print_SingularityFunction method must accept an exp parameter that defaults to None. When exp is provided (not None), it must be appended to the power notation as r"%s^{%s}" % (power, exp). The exp parameter is passed by _print_Pow when dispatching Pow expressions with Function bases.

## References

- `skill_load(name="sympy-sympy-21171", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

