# Lessons — sympy-18189

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pitfall: Test environment issues

Attempted changes failed to run the test suite because of an import error in `sympy/utilities/pytest.py` (module 'py' has no attribute 'test'). Ensure the test environment is correctly configured before validating fixes.

## Lessons
