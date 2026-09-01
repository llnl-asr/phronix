---
name: sympy-sympy-22005
description: The sympy-sympy-22005 subject.
subject: sympy-sympy-22005
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix the univariate polynomial selection condition |
| `I2` | Instructions | sympy-sympy-22005 |
| `R1` | Rules | Check univariate polys vs generators relationship |




## Instructions

### I1 — Fix the univariate polynomial selection condition

In sympy/solvers/polysys.py in the _solve_reduced_system function, change the condition from:
  if len(univariate) == 1:
to:
  if len(univariate) == 1 and len(gens) == 1:
  
This narrows the univariate code path to only single-variable systems, raising NotImplementedError for multi-variable systems with one univariate polynomial.

However, this one-line change may break existing regression tests. A more nuanced check is needed:
- If len(univariate) >= len(gens): the univariate approach is likely valid (one poly per variable), keep the original code
- If len(univariate) == 1 and len(gens) == 1: single variable case, the fix is correct
- If len(univariate) == 1 and len(gens) > 1: the bug case - raise NotImplementedError or use a different approach

The core insight: The condition should check whether the number of univariate polynomials is sufficient for the number of variables (generators).

### I2 — sympy-sympy-22005

What problem it solves:
solve_poly_system((y - 1,), x, y) incorrectly returns [(1,)] instead of raising NotImplementedError. Problem in sympy/solvers/polysys.py line 243 univariate code path not gated on number of system variables.

Key idea:
Add `and len(gens) == 1` to condition so univariate code path only applies when there is exactly one variable in system. This correctly rejects bug cases but is too restrictive for multi-variable regression tests.

Instructions to solve it:
In sympy/solvers/polysys.py change line 243 from `if len(univariate) == 1:` to `if len(univariate) == 1 and len(gens) == 1:`. When len(gens) > 1, condition is False and function raises NotImplementedError.

Constraints and rules:
- Change only affects univariate code path gating
- len(gens) uses function parameter, NOT f.gens assigned later
- Must not regress existing passing tests
- Do not modify test files

Pitfalls and lessons:
Simple fix `and len(gens) == 1` correctly handles the two issue cases (both raise NotImplementedError when they should) but is too restrictive — also rejects valid multi-variable cases where Groebner basis has enough univariate polynomials to solve the system. A more nuanced condition is needed checking whether univariate poly generators are subset of system generators or whether len(univariate) >= len(gens).

## Rules

### R1 — Check univariate polys vs generators relationship

In _solve_reduced_system, the univariate polynomial selection logic has these rules:

1. IF len(univariate) >= len(gens): The univariate approach is likely valid (one polynomial per variable), so the original code path should be used. This handles multi-variable systems where each variable has its own univariate polynomial.

2. IF len(univariate) == 1 and len(gens) == 1: Single variable case. The univariate poly directly solves the system.

3. IF len(univariate) == 1 and len(gens) > 1: Bug case. One univariate polynomial for multiple variables is insufficient. Should raise NotImplementedError with a clear message.

4. IF len(univariate) == 0: No univariate polynomials found. Should fall back to other solving methods.

These rules ensure the fix handles all cases correctly: single variables, multi-variables with sufficient univariate polys, and the bug case.

## References

- `skill_load(name="sympy-sympy-22005", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

