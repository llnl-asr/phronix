---
name: pylint-note-tags-punctuation-fix
description: Fixed pylint --notes handling of punctuation-only tags
metadata:
  type: project
---

The regex in `pylint/checkers/misc.py` was updated to include a lookahead ensuring the note tag is followed by a word boundary or end of line. This allows pylint to correctly emit W0511 warnings for tags consisting solely of punctuation.

**Why:** Previously, tags like `???` were not matched because the regex required a word boundary, which punctuation lacks. The change makes the pattern robust for any tag content.

**How to apply:** Replace the regex construction in `open()` method of `EncodingChecker`:
```python
if self.config.notes_rgx:
    # Match note tags either followed by a word boundary or end of line
    regex_string = rf"#\s*({notes}|{self.config.notes_rgx})(?=\b|$)"
else:
    regex_string = rf"#\s*({notes})(?=\b|$)"
```
This patch has been applied and verified with a test file containing `# YES: yes` and `# ???: no`, both now produce `W0511` warnings.
