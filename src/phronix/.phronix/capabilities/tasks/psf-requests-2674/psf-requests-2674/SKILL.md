---
name: psf-requests-2674
description: Fix for urllib3 exceptions passing through requests API by importing missing exception classes.
subject: psf-requests-2674
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify the failing tests related to urllib3 exceptions |
| `I2` | Instructions | Add missing exception imports |
| `I3` | Instructions | Run tests again to confirm resolution |
| `R1` | Rules | Do not alter existing exception hierarchy |
| `R2` | Rules | Preserve all existing passing tests |

## Instructions

### I1 — Identify the failing tests related to urllib3 exceptions

Run the test suite and note any failures caused by missing `DecodeError` or `TimeoutError` imports.

### I2 — Add missing exception imports

Edit `requests/exceptions.py` and modify the import line:
```diff
@@ -7,7 +7,7 @@ requests.exceptions
-from .packages.urllib3.exceptions import HTTPError as BaseHTTPError
+from .packages.urllib3.exceptions import HTTPError as BaseHTTPError, DecodeError, TimeoutError
```

### I3 — Run tests again to confirm resolution

Execute the test suite; previously failing tests should now pass.

## Rules

### R1 — Do not alter existing exception hierarchy

Only add imports; do not change class definitions or inheritance.

### R2 — Preserve all existing passing tests

Ensure regression tests (141 of 142) continue to pass after the change.
