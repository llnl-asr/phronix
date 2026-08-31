# Lessons — pytest-dev-pytest-11143

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

## Lessons

### L3 — P1 - numeric first expression causes TypeError

When the first statement/expression in a Python module (test file) is a numeric literal (e.g., `1`, `42`), the AST extraction item.value.value returns a Python int rather than a str. Passing this int to is_rewrite_disabled() which does 'PYTEST_DONT_REWRITE' in docstring causes TypeError: argument of type 'int' is not iterable.

### L4 — P2 - the fix is minimal and targeted

A single-line change adding isinstance(doc, str) guard before the is_rewrite_disabled call. This is the correct behavioral guard since a non-string value cannot contain the 'PYTEST_DONT_REWRITE' marker anyway.

### L5 — P3 - verify after fix

Test the fix with: (a) files starting with numeric literal + -k filter, (b) files with normal docstrings, (c) files with PYTEST_DONT_REWRITE marker, (d) all 114 regression tests must pass, (e) the single target test must pass.
