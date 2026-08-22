---
name: ignore-patterns-dot-error
description: Ignore patterns do not prevent dot errors in Flask blueprint names
metadata:
  type: feedback
---

**Finding:** The ignore patterns in configuration (flake8, .gitignore) are unrelated to Flask blueprint name validation. Blueprint name containing a dot is not currently blocked; only endpoint and view function names are checked for dots. To enforce, add validation in Blueprint.__init__.

**Why:** Issue requires raising error for dot‑containing blueprint names; current code lacks such check, so ignoring patterns is ineffective.

**How to apply:** Implement a guard in `Blueprint.__init__` raising `ValueError` if `"." in name`. Update documentation accordingly.
