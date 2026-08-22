---
name: normalize-paths-before-ignore
description: Normalize file paths to forward‑slash style before applying ignore‑list checks.
metadata:
  type: feedback
---

Directive: In `_is_ignored_file`, normalize `element` with `os.path.normpath(element).replace(os.sep, "/")` before extracting basename and applying ignore patterns.\nWhy: Consistent path format ensures regexes work across OSes and matches the intended ignore‑path patterns.
