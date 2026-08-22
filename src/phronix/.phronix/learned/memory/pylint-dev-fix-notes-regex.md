---
name: pylint-dev-fix-notes-regex
description: Fix notes regex to handle punctuation-only tags
metadata:
  type: project
---

Adjusted the regex in pylint/checkers/misc.py from using a word boundary to a lookahead that matches non-word characters or end of string. This ensures note tags that are entirely punctuation (e.g., "???") are correctly recognized by the `--notes` option.

**Why:** The original pattern `#\s*({notes})\b` failed to match punctuation-only tags because `\b` requires a word boundary. Replacing it with `(?=\W|$)` fixes the issue.

**How to apply:** The edit replaces the regex string in the `open` method of `EncodingChecker`.
