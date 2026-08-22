# Lessons — pylint-fixme-codetag

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Regex change broke non‑alphanumeric fixme detection

**2026-08-21** — The attempted change added a negative look‑ahead (?!\w) after notes/notes_rgx in EncodingChecker, which prevented detection of non‑alphanumeric fixme tags. The test test_non_alphanumeric_codetag still fails. Future fixes should avoid adding (?!\w) to this regex.
