---
name: punctuation-note-tag-behavior
description: Pylint ignores punctuation-only note tags due to word boundary in regex
metadata:
  type: project
---

The EncodingChecker builds a regex for note tags with a trailing word boundary (`\b`). Since punctuation-only tags contain no word characters, the word boundary never matches, causing such tags to be ignored and no W0511 warning is emitted.
