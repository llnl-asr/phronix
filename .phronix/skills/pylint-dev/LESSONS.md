# Lessons — pylint-dev

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Punctuation-only tags not flagged by pylint note parser

**2026-08-21** — Punctuation-only tags (e.g., "!!!") are not flagged as fixme notes by pylint's note parser, causing them to be ignored during linting.
