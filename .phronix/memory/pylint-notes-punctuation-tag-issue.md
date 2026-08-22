---
name: pylint-notes-punctuation-tag-issue
description: Regex word boundary prevents matching punctuation-only note tags in pylint --notes
metadata:
  type: project
---

The `EncodingChecker` builds a regex string for note tags that includes a word‑boundary (`\b`). When a note tag consists only of punctuation characters (e.g., `???`), the word‑boundary prevents a match, causing the `--notes` option to ignore such tags. Removing the `\b` alone does not fix the issue; the regex must be adjusted to explicitly allow punctuation‑only tags.

**Why:** Word boundary requires a transition between word and non‑word characters, which never occurs for punctuation‑only tags.

**How to apply:** Change the regex construction to include a pattern that matches punctuation‑only tags, such as adding `[\p{Punct}]+` or a permissive alternative.

**Type:** project
