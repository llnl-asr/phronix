# Lessons — sympy-sympy-16988

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Duplicate removal may conflict with SymPy's internal processing

The deduplication code can interfere with SymPy's canonical ordering, leading to unexpected behavior.

## Lessons

### L1 — Import error originates from outdated `py` library usage

The AttributeError `module 'py' has no attribute 'test'` is due to using `py.test` instead of `pytest`. Fix by updating the import in `sympy/utilities/pytest.py`.
