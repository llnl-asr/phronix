---
name: pylint-notes-punctuation-fix
description: Fix regex to handle punctuation-only note tags in --notes option
metadata:
  type: project
---

**Why:** The original regex required a word boundary after note tags, causing tags consisting solely of punctuation (e.g., "???") to be ignored, breaking the intended `--notes` behaviour.
**How to apply:** Updated `regex_string` construction in `pylint/checkers/misc.py` to use `(?:\b|$)` so the pattern matches either a word boundary or end of string, ensuring punctuation-only notes are recognized.
---
**Change:**
```python
-        if self.config.notes_rgx:
-            regex_string = rf"#\s*({notes}|{self.config.notes_rgx})\b"
-        else:
-            regex_string = rf"#\s*({notes})\b"
+        if self.config.notes_rgx:
+            regex_string = rf"#\s*({notes}|{self.config.notes_rgx})(?:\b|$)"
+        else:
+            regex_string = rf"#\s*({notes})(?:\b|$)"
```
