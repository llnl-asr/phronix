# Lessons — django-django-11019

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Changing warning text broke tests

**2026-08-31** — The test suite expected the original warning message text. Modifying the warning message caused failures even though the order issue was fixed. Future fixes should either update the tests to check the merged order instead of warning text, or keep the original warning message format.
