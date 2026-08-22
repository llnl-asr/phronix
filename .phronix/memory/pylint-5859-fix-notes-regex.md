---
name: pylint-5859-fix-notes-regex
description: Adjust regex to match punctuation-only note tags
metadata:
  type: project
---

**Why:** The original regex used a word‑boundary (`\b`) after the note pattern, which prevents tags composed solely of punctuation (e.g. `???`) from being recognised as fixme notes. This caused `pylint --notes="YES,???"` to miss the second warning.

**How to apply:** In `pylint/checkers/misc.py` the regex construction in `open()` is changed to drop the trailing `\b`. The new pattern matches any of the configured notes or the optional custom regex without requiring a word boundary.

**Result:** Both note tags are now detected, and `pylint` correctly emits `W0511` for each line.

[[pylint-issue-5859]]
