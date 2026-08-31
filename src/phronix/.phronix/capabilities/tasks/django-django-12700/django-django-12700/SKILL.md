---
name: django-django-12700
description: SafeExceptionReporterFilter.cleansing_setting() not recursively cleansing sensitive values in nested iterables (lists, tuples) within Django settings. The method only handles dict types, leaving sensitive data exposed in list/tuple structures.
subject: django-django-12700
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | what-problem-it-solves |
| `I2` | Instructions | the-key-idea |
| `I3` | Instructions | instructions-to-solve-it |
| `I4` | Instructions | constraints-and-rules |
| `I5` | Instructions | pitfalls-and-lessons |
| `R1` | Rules | R1 |
| `R2` | Rules | R2 |
| `R3` | Rules | R3 |
| `R4` | Rules | R4 |
| `R5` | Rules | R5 |

## Instructions

### I1 — what-problem-it-solves

A later run arrives with a failing test where sensitive keys (API, TOKEN, KEY, SECRET, PASS, SIGNATURE) in Django settings nested inside lists/tuples are not being cleansed. The symptom: get_safe_settings() returns un-cleansed dicts within list/tuple values. The fix must recognize that settings values can be lists, tuples, or other iterables (not just dicts) and recursively cleanse each element.

### I2 — the-key-idea

The email field is not always called `email` — similarly, the sensitive key is not always at the top level. Sensitive data can be nested inside lists, tuples, or dicts within settings. The one insight: cleanse_setting() must recurse into list and tuple values the same way it recurses into dict values, preserving the original container type.

### I3 — instructions-to-solve-it

1. In django/views/debug.py, find the cleanse_setting() method
2. After the existing `elif isinstance(value, dict):` branch (currently lines 91-92), add a new branch: `elif isinstance(value, (list, tuple)):` that recursively processes each item
3. Use `type(value)(self.cleanse_setting(key, item) for item in value)` to preserve list vs tuple type
4. The existing `else` branch already handles all other types (including strings, sets, etc.) correctly by returning them as-is
5. Run the test suite to verify: `python -m pytest tests/view_tests/tests/test_debug.py -k cleanse_setting -v` — all 77 regression tests + 1 target test must pass

### I4 — constraints-and-rules

Keeps passing: all 77 existing regression tests in test_debug.py. Must not touch: the `except TypeError` handler, the `get_safe_settings()` method, any test files. The fix is purely additive — only adds the list/tuple branch after the dict branch. The invariant: after the fix, cleanse_setting must recursively cleanse sensitive keys at ANY nesting depth, whether in dicts, lists, or tuples.

### I5 — pitfalls-and-lessons

Pitfall: Only handling `dict` returns nested dicts un-cleansed when they're inside lists/tuples (the exact bug reported). Pitfall: Forgetting `type(value)(...)` causes a list to become a generator instead of a list. Pitfall: Including `str` in the isinstance check would recurse into string characters, breaking everything. Lesson: The original `isinstance(value, dict)` check was too narrow — it needed to also cover list and tuple types while excluding strings. The fix that adds `elif isinstance(value, (list, tuple))` after the dict branch resolves this.

## Rules

### R1 — R1

Must add the list/tuple branch AFTER the existing dict branch, not before or replacing it

### R2 — R2

Must use `type(value)(...)` to preserve the original container type (list stays list, tuple stays tuple)

### R3 — R3

Must not include str in the isinstance check — strings are iterable but should be returned as-is

### R4 — R4

Must not modify any test files — only edit django/views/debug.py

### R5 — R5

All 77 regression tests + 1 target test must pass after the fix

## References

- `skill_load(name="django-django-12700", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
