---
name: pylint-note-tags-punct-flag-fix
description: Add support for punctuation-only tags in pylint --notes option
metadata:
  type: reference
---

**Why:** The current regex uses a word‑boundary, causing tags like "???" to never match, so they are ignored despite being listed in `--notes`.
**How to apply:** Update the regex in `pylint/checkers/misc.py` to remove the trailing `\b` or replace it with a pattern that matches any non‑whitespace characters, allowing punctuation‑only tags to be recognized.
