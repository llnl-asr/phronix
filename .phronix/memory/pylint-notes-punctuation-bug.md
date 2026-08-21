---
name: pylint-notes-punctuation-bug
description: Pylint --notes option ignores note tags that are entirely punctuation
metadata:
  type: project
---

The current implementation of the `--notes` option in Pylint builds a regex that includes a word boundary (`\b`) at the end. This means that note tags consisting only of punctuation characters (e.g., `!!!`) are not matched because there is no word character at the end to satisfy the boundary. As a result, such tags do not trigger the expected warnings (`W0511`).
