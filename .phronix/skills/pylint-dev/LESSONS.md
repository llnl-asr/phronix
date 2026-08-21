# Lessons — pylint-dev

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Lookahead regex breaks fixme detection for non-alphanumeric codetags

**2026-08-21** — Adding a positive lookahead `(?=\s|$)` to the regex for notes and notes_rgx in `pylint/checkers/misc.py` prevented the fixme checker from emitting messages for comment codetags that are not followed by whitespace. The test `test_non_alphanumeric_codetag` still fails. Future changes should preserve the original pattern or ensure end‑of‑line is matched without requiring a space.
