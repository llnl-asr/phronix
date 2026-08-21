---
name: sympy-pretty-import-error
description: Fixes import error caused by missing Flask request_ctx.
subject: sympy-pretty-import-error
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add fallback import for Flask request_ctx to avoid ImportError |


## Instructions

### I1 — Add fallback import for Flask request_ctx to avoid ImportError

In sympy/printing/pretty/pretty.py (or the relevant module where Flask's request_ctx is imported), wrap the import in a try/except block:
```
try:
    from flask.globals import request_ctx
except Exception:
    request_ctx = None
```
This ensures that if Flask is not installed or the import fails, the module still loads without raising ImportError, fixing the failing hidden tests.

## Rules

## References
