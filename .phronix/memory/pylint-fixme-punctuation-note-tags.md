---
name: pylint-fixme-punctuation-note-tags
description: Pylint fixme checker regex word boundary fails for punctuation-only note tags
metadata:
  type: lesson
---

**Symptom:** Pylint's `--notes` option fails to detect fixme warnings (W0511) when note tags are entirely punctuation (e.g., "???", "!!!", "...").

**Root cause:** The regex pattern in `pylint/checkers/misc.py` uses `\b` (word boundary) which requires a word character (`\w`) on at least one side of the boundary. Punctuation-only tags contain no word characters, so `\b` never matches them.

**Example:** Pattern `#\s*(???)\b` searches for "???" followed by a word boundary, but since "?" is not a word character, there's no boundary between "?" and the following character (whether it's ":", " ", or end-of-string).

**Exact fix:** Replace `\b` with positive lookahead `(?=:|\s|$)` which explicitly checks for valid separators (colon, whitespace, or end-of-string) without consuming them:
- Line 124: `rf"#\s*({notes}|{self.config.notes_rgx})(?=:|\s|$)"`  
- Line 126: `rf"#\s*({notes})(?=:|\s|$)"`

**Why:** Alternative negative lookahead `(?!\w)` also works but the positive lookahead is more explicit about what constitutes a valid tag boundary.

**How to apply:** Edit pylint/checkers/misc.py, replace both occurrences of `\b` in the open() method (lines 124 and 126).
