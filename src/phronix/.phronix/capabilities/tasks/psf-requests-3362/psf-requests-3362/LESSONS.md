# Lessons — psf-requests-3362

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — P1: Fallback with getattr('email') fails

Using `getattr(user, 'email', '')` does not work because the actual field is named `email_address`; the fallback returns empty leading to downstream type errors.

## Lessons

### L1 — Attempt 3 produced no code changes; tests expecting correct handling o

**2026-08-31** — Attempt 3 produced no code changes; tests expecting correct handling of streamed responses failed because the skill only described the issue without implementing a fix. The missing implementation caused the test suite to raise AssertionError when checking decoded content.
