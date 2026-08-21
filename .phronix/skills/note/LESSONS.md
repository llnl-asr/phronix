# Lessons — note

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Fix regex for punctuation-only fixme notes

**2026-08-21** — Symptom: Pylint did not emit W0511 for fixme tags that consist only of punctuation (e.g., `# ???: no`). Root cause: The regex used a word boundary (`\b`) which fails when the note ends with punctuation or end of line. Fix: Update the regex to use a look‑ahead allowing whitespace or end of string: `regex_string = rf"#\s*({notes}|{self.config.notes_rgx})(?=\s|$)` for `notes_rgx` case, and similarly for explicit notes. This change captures tags before whitespace or end of line, ensuring all fixme notes are detected.
