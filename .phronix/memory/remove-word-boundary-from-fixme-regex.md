---
name: remove-word-boundary-from-fixme-regex
description: Fix regex for encoding checker notes by removing trailing word boundary
metadata:
  type: feedback
---

**Why:** The previous regex used `\b` which prevented matching notes that were followed by punctuation or end of line, causing false negatives in detecting fixme notes. Removing the word boundary allows the pattern to match notes regardless of following characters.
**How to apply:** Update `pylint/checkers/misc.py` in `EncodingChecker` to use `regex_string = rf"#\s*({notes}|{self.config.notes_rgx})"` for both branches, as done in the recent patch.
