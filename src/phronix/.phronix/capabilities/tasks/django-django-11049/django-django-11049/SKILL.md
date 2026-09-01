---
name: django-django-11049
description: The django-django-11049 subject.
subject: django-django-11049
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix DurationField error message format |
| `I2` | Instructions | DurationField error message format fix |
| `I3` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Fix DurationField error message format

Change the DurationField invalid format error message in django/db/models/fields/__init__.py from "[DD] [HH:[MM:]]ss[.uuuuuu]" to "[DD] [[HH:]MM:]ss[.uuuuuu]".

File: django/db/models/fields/__init__.py
Line: ~1590 (inside DurationField.default_error_messages['invalid'])
Change: "[DD] [HH:[MM:]]ss[.uuuuuu]" → "[DD] [[HH:]MM:]ss[.uuuuuu]"

WHY this form and not the obvious one:
- The current format "[HH:[MM:]]" suggests both hours and minutes are individually optional
- But the actual regex (standard_duration_re) shows: seconds are mandatory, minutes are optional but when hours are present, minutes must also be present
- The correct format "[[HH:]MM:]" properly conveys: minutes are always the base time component, and hours are optional only when minutes are provided
- This matches the actual parsing behavior: "14:00" → 14 minutes (not 14 seconds), "1:14:30" → 1 hour 14 minutes 30 seconds

What the tests checked:
- test_durationfield tests (1 target test + 8 regression tests)
- test_invalid_string specifically checks the error message format for invalid duration input
- All 9 tests passed after the fix (1 target test + 8 regression tests)

### I2 — DurationField error message format fix

Fix the DurationField error message format: change the bracket structure from "[DD] [HH:[MM:]]ss[.uuuuuu]" to "[DD] [[HH:]MM:]ss[.uuuuuu]" in django/db/models/fields/__init__.py line 1590.

### I3 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/models/fields/__init__.py b/django/db/models/fields/__init__.py
index f32ce64629..71005490f3 100755
--- a/django/db/models/fields/__init__.py
+++ b/django/db/models/fields/__init__.py
@@ -1587,7 +1587,7 @@ class DurationField(Field):
     empty_strings_allowed = False
     default_error_messages = {
         'invalid': _("'%(value)s' value has an invalid format. It must be in "
-                     "[DD] [HH:[MM:]]ss[.uuuuuu] format.")
+                     "[DD] [[HH:]MM:]ss[.uuuuuu] format.")
     }
     description = _("Duration")
```

## Rules
