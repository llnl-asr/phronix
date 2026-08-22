---
name: pylint-fix-note-regex-colon
description: Fix regex in misc.py to handle note followed by colon
metadata:
  type: project
---

**Why:** Pylint's `--notes` option ignored notes that were followed by a colon, causing missing W0511 warnings for such notes.
**How to apply:** The regex in `pylint/checkers/misc.py` was changed from `rf"#\s*({notes})(?=\W|$)"` to `rf"#\s*({notes})(?=\s*:|$)"` to correctly match notes followed by a colon.
[[pylint-fix-note-regex-colon]]
