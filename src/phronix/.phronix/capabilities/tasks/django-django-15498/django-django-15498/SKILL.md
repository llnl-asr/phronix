---
name: django-django-15498
description: Fix handling empty string for If-Modified-Since header in Django's static file serving. The issue is that an empty If-Modified-Since header causes TypeError because re.match() returns None when the header value is empty, and the code doesn't handle this case.
subject: django-django-15498
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | what-problem-it-solves |
| `I2` | Instructions | key-idea |
| `I3` | Instructions | instructions-to-solve-it |
| `I4` | Instructions | constraints-and-rules |
| `I5` | Instructions | pitfalls-and-lessons |
| `I6` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — what-problem-it-solves

When the If-Modified-Since header is present but empty (e.g., 'If-Modified-Since: '), Django's was_modified_since() function in django/views/static.py raises TypeError: 'NoneType' object is not subscriptable. This crashes the server instead of gracefully handling the empty header.

### I2 — key-idea

The regex r"^([^;]+)(; length=([0-9]+))?$" requires at least one character ([^;]+), so when the header value is empty string "", re.match() returns None. Adding a guard clause to check if matches is None and return True (safe default) prevents the TypeError.

### I3 — instructions-to-solve-it

1. File: django/views/static.py
2. Function: was_modified_since
3. After the regex match (after line 62), add: if matches is None:  # NEW: handle empty/invalid headers\n       return True\n This returns True (meaning 'resource was modified since last download') as the safe default, consistent with how None headers and other parsing failures are already handled.

### I4 — constraints-and-rules

- Must not break any of the 25 existing regression tests
- The target test test_was_modified_since_empty_string must pass
- Must return True for empty/malformed headers (safe default that triggers full content resend)
- Must not change behavior for valid If-Modified-Since headers
- The fix must be in django/views/static.py only, not in test files or other modules

### I5 — pitfalls-and-lessons

- Previous attempt modified django/test/utils.py (override_settings class) which addressed a different issue but did NOT fix the target test
- The fix must be in the was_modified_since function itself, not in test utilities
- The except clause only catches (AttributeError, ValueError, OverflowError) but NOT TypeError, so we must guard before the subscript operation
- Returning True is the correct safe default: it causes the server to resend full content rather than crash
- The fix is just 2 lines: the if matches is None: return True guard after the regex match

### I6 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/views/static.py b/django/views/static.py
index 1c558a53ff..46a9eba80f 100755
--- a/django/views/static.py
+++ b/django/views/static.py
@@ -129,6 +129,8 @@ def was_modified_since(header=None, mtime=0, size=0):
         if header is None:
             raise ValueError
         matches = re.match(r"^([^;]+)(; length=([0-9]+))?$", header, re.IGNORECASE)
+        if matches is None:
+            return True
         header_mtime = parse_http_date(matches[1])
         header_len = matches[3]
         if header_len and int(header_len) != size:
```

## Rules
