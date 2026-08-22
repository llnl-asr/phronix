---
name: pylint-ignore-paths-failure
description: pylint ignore-paths patterns ignored due to punctuation handling
metadata:
  type: project
---

Finding: pylint's ignore-paths option does not correctly ignore files when patterns consist solely of punctuation (e.g., "???").
**Why:** The internal parser treats such patterns as invalid tokens, causing them to be skipped.
**How to apply:** Ensure ignore-paths patterns contain at least one alphanumeric character or use more explicit glob patterns. Update pylint configuration to avoid punctuation-only entries.
