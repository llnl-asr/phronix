# Lessons — pytest-dev-pytest-5413

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Avoid replacing formatted output with plain message

**2026-08-29** — Replacing `ExceptionInfo.__str__` to return only `str(self.value)` removed the required formatted representation, causing test failures. Preserve the original format or conditionally delegate to it.
