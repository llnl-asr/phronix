---
name: psf-requests-2317-fix
description: Fix for bytes-to-string conversion issue in requests sessions method handling. In requests/sessions.py line 428, `method = builtin_str(method)` was converting bytes strings like b'GET' to the literal string "b'GET'" instead of "GET". The fix uses to_native_string(method) which properly decodes bytes using ASCII encoding while returning strings unchanged.
subject: requests sessions method conversion
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix bytes-to-string conversion in sessions.py |
| `R1` | Rules | Use to_native_string for method conversion |

## Instructions

### I1 — Fix bytes-to-string conversion in sessions.py

In requests/sessions.py line 428, change `method = builtin_str(method)` to `method = to_native_string(method)`. The to_native_string function (already imported from .utils on line 21) properly handles both string and bytes inputs: if the input is already a string, it returns it as-is; if it's bytes, it decodes it using ASCII encoding. This fixes the issue where HTTP method values like b'GET' were being converted to the literal string 'b\'GET\'' instead of 'GET', causing 404 Not Found responses.

## Rules

### R1 — Use to_native_string for method conversion

Always use to_native_string(method) instead of builtin_str(method) when converting HTTP method values in requests/sessions.py. The to_native_string function properly decodes bytes strings while preserving normal string inputs.

## References

- `skill_load(name="psf-requests-2317-fix", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
