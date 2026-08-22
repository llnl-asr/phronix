---
name: note-punctuation-fix-failed
description: Attempt to fix punctuation-only note tags failed and caused regression
metadata:
  type: feedback
---

**Why:** The previous attempt only changed file permissions of misc.py without modifying the note detection logic, so the '--notes' option still ignored punctuation-only tags. It also introduced a regression in test_dont_trigger_on_todoist.
**How to apply:** Implement proper handling of punctuation-only note tags in pylint/checkers/misc.py by adjusting the regex used for fixme detection to include tags consisting solely of punctuation. Ensure existing tests, especially TestFixme.test_dont_trigger_on_todoist, remain passing.
