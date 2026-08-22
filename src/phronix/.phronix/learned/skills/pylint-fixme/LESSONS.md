# Lessons — pylint-fixme

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Regex must allow end-of-line for punctuation-only note tags

**2026-08-21** — Symptom: `pylint --notes` ignored tags like `# ???: no` because the regex used `\b` which fails when the tag contains only punctuation. Root cause: word boundary does not match after punctuation. Fix: change the regex to `rf"#\s*({notes}|{self.config.notes_rgx})(?:\b|$)"` so it also matches end-of-string. This ensures punctuation-only tags are recognized and reported as fixme warnings.
