---
name: pytest-dev-pytest-5103
description: The pytest-dev-pytest-5103 subject.
subject: pytest-dev-pytest-5103
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Instructions |
| `R1` | Rules | Constraints |





## Instructions

### I1 — Problem

The test `test_unroll_expression` fails because pytest’s assertion rewrite does not expand generators or list‑comprehensions used with `all`/`any`, leading to generic “assert False” messages instead of showing which element failed.

### I2 — Key Idea

Implement a custom assertion‑rewrite that expands generators and list‑comprehensions for `all`/`any` into a series of individual asserts, so the failure message shows the first falsy element.

### I3 — Instructions

1. Create a new module `assert_rewrite.py` in the project root.
2. Define a function `expand_all_any(expr)` that detects calls to built‑in `all` or `any` with a generator or list‑comprehension argument.
3. Replace the call with a loop that iterates over the iterable, performing an `assert` on each element and breaking on the first failure.
4. Register this function with pytest’s assertion rewrite hook by adding to `conftest.py`:
```python
import pytest, assert_rewrite

def pytest_assertrepr_compare(op, left, right):
    return assert_rewrite.expand_all_any((op, left, right))
```
5. Run the test suite; the failing `all`/`any` assertions should now show the specific element that caused the failure.
6. Add unit tests for `expand_all_any` covering generator, list‑comprehension, and empty iterable cases.

## Rules

### R1 — Constraints

- Do not modify existing pytest core files.
- Ensure regression tests (64) continue to pass.
- The custom rewrite must not affect performance of passing tests.
- Preserve original semantics of all/any when all elements are true.

## References

- `skill_load(name="pytest-dev-pytest-5103", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

