---
name: note-parsing-non-fixme
description: Note parser does not flag punctuation-only tags as fixme
metadata:
  type: project
---

**Why:** The regex for fixme detection only matches alphanumeric tags defined in `config.notes` (e.g., FIXME, XXX, TODO) as whole words following a '#'. Pure punctuation strings like "!!!" lack alphanumeric characters and thus do not form a word boundary match, meaning they are correctly ignored as non-fixme notes.

**How to apply:** No code change is needed; ensure any custom `notes-rgx` does not unintentionally include punctuation-only patterns unless they should be flagged.
