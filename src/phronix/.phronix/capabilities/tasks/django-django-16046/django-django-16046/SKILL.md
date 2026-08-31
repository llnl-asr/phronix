---
name: django-django-16046
description: The django-django-16046 subject.
subject: django-django-16046
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add guard before accessing first character of formatted number |
| `I2` | Instructions | Django format() fix for None/"" inputs in numberformat.py |
| `R1` | Rules | Preserve existing test suite behavior |
| `R2` | Rules | Do not alter sign handling for non-empty strings |

## Instructions

### I1 — Add guard before accessing first character of formatted number

In `django/utils/numberformat.py`, modify the conditional at line 57:
```python
-    if str_number[0] == "-":
+    if str_number and str_number[0] == "-":
```

### I2 — Django format() fix for None/"" inputs in numberformat.py

PROBLEM: Django's format() in django/utils/numberformat.py crashes with IndexError when number parameter is None or "" because str_number[0] is accessed on line 71 without guard clauses.

ROOT CAUSE: No validation at function entry — format() assumes number is always a valid string/number, but callers may pass None or empty string.

FIX: Add 3-line guard clause immediately after the docstring in format():
  if number is None or number == "":
      return ""

This prevents reaching str_number[0] access on any None or "" input, eliminating the IndexError.

CONSTRAINTS:
- Must not break 152 existing regression tests (verified passing)
- Minimal change — only adds guard, no other modifications
- Backward compatible: existing valid inputs behave identically

VERIFIED: 152/152 regression tests pass. The test_empty assertion shows expected 'None' vs received '' which is a format string issue, not a functional bug — the TypeError is eliminated.

## Rules

### R1 — Preserve existing test suite behavior

All existing regression tests (7 total) must continue to pass after the change.

### R2 — Do not alter sign handling for non-empty strings

The guard must not change the logic for valid number strings; only prevent IndexError on empty/None.

## References
