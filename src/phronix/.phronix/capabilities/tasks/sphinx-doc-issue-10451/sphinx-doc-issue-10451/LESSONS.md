# Lessons — sphinx-doc-issue-10451

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — P1 — Fallback attribute approach failed

**2026-08-27** — Attempt 1 added a fallback attribute access, but other code still expected a real `email` field, leading to AttributeError and no test passing.
