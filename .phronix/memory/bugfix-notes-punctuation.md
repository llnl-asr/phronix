---
name: bugfix-notes-punctuation
description: Fix pylint --notes handling for punctuation-only tags
metadata:
  type: project
---

Implemented regex change in `pylint/checkers/misc.py` to use a lookahead `(?=\s|$)` instead of word boundary, ensuring tags like "???" are matched.

**Why:** The original regex used `\b` which fails for punctuation-only notes, causing fixme warnings to be missed.

**How to apply:** Updated the regex construction in `open` method for both cases (with and without custom regex).

**Why this matters:** Aligns pylint behavior with expected output for `--notes` option, addressing issue described in `issue.md`.

**Related memories:** [[bugfix-notes-punctuation]]
