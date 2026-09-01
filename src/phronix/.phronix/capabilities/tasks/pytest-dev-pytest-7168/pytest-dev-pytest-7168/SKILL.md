---
name: pytest-dev-pytest-7168
description: The pytest-dev-pytest-7168 subject.
subject: pytest-dev-pytest-7168
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis for pytest-dev-pytest-7168 - saferepr exception handling |


## Instructions

### I1 — Diagnosis for pytest-dev-pytest-7168 - saferepr exception handling

Problem: _format_repr_exception in saferepr.py fails when __getattribute__ raises and repr() is called. Exception's __repr__ may itself fail. Nested exception contexts create chain failures. Current try/except only catches one level.

Root cause: _format_repr_exception calls _try_repr_or_str(exc) which calls repr(exc). If repr fails, it falls back to type name. But when called from SafeRepr.repr() during its own exception handling, the outer call may fail before inner protection applies. test_broken_getattribute demonstrates this.

Fix needed: _format_repr_exception must have a top-level fallback catching ALL exceptions from the formatting chain, returning just the exception type name.

Why this matters: Without fix, classes with broken __getattribute__ or __repr__ cause crashes/RecursionError in pytest error reporting.

## Rules

## References
