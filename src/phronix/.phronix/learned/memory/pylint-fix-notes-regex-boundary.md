---
name: pylint-fix-notes-regex-boundary
description: Remove word-boundary from notes regex to detect punctuation-only tags
metadata:
  type: project
---

In pylint's `pylint/checkers/misc.py`, the regex used to match note tags included a word‑boundary (`\b`). This prevented tags consisting solely of punctuation (e.g., `???`) from being recognized, causing `--notes` to miss such warnings. The fix removes the trailing word‑boundary from both the combined and simple regex constructions, allowing the pattern to match any specified tag regardless of surrounding characters.

**Why:** Ensures `pylint --notes="YES,???"` correctly reports both `YES` and `???` fixme warnings as required by issue #5859.

**How to apply:** Edit the two `regex_string` assignments in `EncodingChecker.open`:
```
- regex_string = rf"#\s*({notes}|{self.config.notes_rgx})\b"
+ regex_string = rf"#\s*({notes}|{self.config.notes_rgx})"

- regex_string = rf"#\s*({notes})\b"
+ regex_string = rf"#\s*({notes})"
```
