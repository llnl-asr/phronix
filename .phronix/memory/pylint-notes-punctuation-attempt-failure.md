---
name: pylint-notes-punctuation-attempt-failure
description: Attempt to fix pylint --notes punctuation bug failed; no diff generated
metadata:
  type: feedback
---

**What happened:** The agent attempted to address the issue where `pylint --notes` ignores note tags consisting only of punctuation (e.g., "???"). The attempt produced no patch (empty diff) and no narrative output.\n\n**Outcome:** The issue remains unresolved; the existing lesson in `pylint-notes-punctuation` (removing trailing word boundary from the regex) was not applied.\n\n**Why this is recorded:** Future sessions can quickly see that a prior attempt did not succeed, avoiding repeat of the same approach that produced no changes. This memory serves as a durable fact about the attempt's failure.\n\n**How to apply:** When working on this issue, check existing lessons (see `pylint-notes-punctuation` skill) and ensure any changes are applied correctly; do not assume an attempt without a diff succeeded.\n
