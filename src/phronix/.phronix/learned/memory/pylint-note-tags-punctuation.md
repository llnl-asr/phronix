---
name: pylint-note-tags-punctuation
description: pylint --notes option ignores tags that are only punctuation
metadata:
  type: reference
---

Symptom: Using `pylint --notes` with a tag consisting solely of punctuation (e.g., `???`) does not produce a fixme warning (W0511).
Root cause: Pylint's note tag parser skips tags that have no alphanumeric characters.
Fix: Avoid pure punctuation tags; include at least one letter or number in each note tag (e.g., `NOTE1`).

**Why:** The parser treats such tags as empty and does not emit warnings, leading to missed issues.
**How to apply:** When using `pylint --notes`, ensure each tag contains alphanumeric characters.
