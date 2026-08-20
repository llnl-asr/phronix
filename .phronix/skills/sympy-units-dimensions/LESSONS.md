# Lessons — sympy-units-dimensions

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Test grading in this sandbox can fail with "No module named pytest" — not a real code failure

In attempt-3, the grading harness reported the sole failure reason as `/opt/miniconda3/envs/testbed/bin/python: No module named pytest`. That means the test run itself errored out before evaluating the fix — this is an environment/invocation problem (pytest not installed/importable in that env), not evidence the code change is wrong. Before concluding a fix doesn't work, check whether the test command actually executed (look for real assertion output) rather than trusting a bare "0 of N passing" count that may stem from a broken test invocation. If pytest is missing, try running the test via sympy's own test runner (`bin/test` or `python -m sympy.testing.runtests`) instead of `pytest`.

## Lessons

### L1 — Function-arg branch of _collect_factor_and_dimension returns wrong tuple shape

**2026-08-19** — Bug: `SI._collect_factor_and_dimension()` raises ValueError on dimensionless-argument functions like `exp(second/(farad*ohm))`, e.g. inside `100 + exp(expr)`.

Root cause location: `sympy/physics/units/unitsystem.py`, the `elif isinstance(expr, Function):` branch of `_collect_factor_and_dimension` (~line 192-198 in the pre-fix file). All other branches return a 2-tuple `(factor, dimension)`. This branch instead does:
```
return (expr.func(*(f[0] for f in fds)), *(d[1] for d in fds))
```
i.e. it splices in one dimension per function argument, so for an N-arg function it returns an (N+1)-tuple, not a 2-tuple. Callers unpack `factor, dim = ...` and get garbage/wrong dim for multi-arg cases, and even for 1-arg functions the raw arg dimension (e.g. time/(capacitance*impedance)) is passed through unchecked/uncollapsed instead of being validated as dimensionless and normalized to `Dimension(1)`.

Attempt 1 (this repo, unresolved) tried fixing only the dimensionless-collapse part:
```python
dims = [Dimension(1) if self.get_dimension_system().is_dimensionless(d[1]) else d[1] for d in fds]
return (expr.func(*(f[0] for f in fds)), *dims)
```
This still returns a variadic tuple (still wrong shape for multi-arg functions) and did not fix the target test `test_issue_24062` — confirmed failing after this change (target tests 0/1 passed, per attempt-notes.md). Do not repeat this exact patch.

Hypothesis (unverified — would need to actually run the fix): the correct fix must (a) always return a 2-tuple, (b) for each function argument, check `is_dimensionless(arg_dim)`; if not raise/keep as-is only when dimensionally consistent, (c) the function's overall *dimension* result should be `Dimension(1)` (dimensionless) when the function itself is one like exp/log/sin whose args must be dimensionless — not simply forwarding argument dimensions. Confirm by re-reading how non-Function branches structure the return and checking sympy's actual upstream fix for issue 24062 before reimplementing.

### L2 — attempt-3: Function-arg dimensionless fix in unitsystem.py still failed test_issue_24062

**2026-08-19** — Symptom: `SI._collect_factor_and_dimension(100 + exp(second/(farad*ohm)))` raises ValueError even though the exponent is actually dimensionless.

Attempt-3's fix, in `UnitSystem._collect_factor_and_dimension` (sympy/physics/units/unitsystem.py, `Function` branch): replaced each arg's returned dimension with `Dimension(1)` when `is_dimensionless(d[1])` is true, i.e.

```python
elif isinstance(expr, Function):
    fds = [self._collect_factor_and_dimension(arg) for arg in expr.args]
    dims = [Dimension(1) if self.get_dimension_system().is_dimensionless(d[1]) else d[1] for d in fds]
    return (expr.func(*(f[0] for f in fds)), *dims)
```

This still left `test_issue_24062` failing (0/1 target tests, graded as NOT resolved). The patch only *labels* dimensionless args as Dimension(1) but does not actually validate/raise when a Function arg is NOT dimensionless — it just passes through whatever dimension was computed, changing the returned dimension tuple shape/semantics without confirming it matches what the test expects. Root cause of the remaining failure was not diagnosed further in this attempt (test runner itself was broken — see pitfall below) — treat this exact diff as a starting point that needs more validation against the actual expected exception behavior for non-dimensionless Function args, not as a working fix.

Do not just re-apply this same one-line change and assume it's correct; it was tried and graded as failing.
