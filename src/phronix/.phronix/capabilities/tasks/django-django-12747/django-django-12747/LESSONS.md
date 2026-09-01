# Lessons — django-django-12747

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Incorrect normalization of QuerySet.delete() return broke tests

Attempted to normalize the return of `QuerySet.delete()` by converting a zero rows‑count dict to an empty dict. This change caused `AttributeError: 'int' object has no attribute 'values'` in several deletion tests because the code assumed `_rows_count` was a dict and called `.values()`. The fix also broke the expected return format for callers that rely on the original `(deleted, rows_count)` tuple where `rows_count` is an integer. Revert the change and instead handle the empty‑dict case in the caller or update tests accordingly.

### P2 — P1

P1 — Incorrect normalization of QuerySet.delete() return broke tests. The attempted change converted zero rows-count dict to empty dict and altered the return signature, causing AttributeError and mismatched expected tuples. Reverting to original `(int, dict)` with proper handling fixes the failures.

## Lessons

### L1 — Pitfall: masking missing attribute with getattr

**2026-08-29** — Attempt 1 used `getattr(user, 'email', '')` which hid the missing attribute but downstream code still required a real email, causing validation failures. Masking does not fix the root cause.

### L2 — Pitfall: defined helper not integrated

**2026-08-29** — Attempt 2 defined `get_email_field_name()` but never called, so the auth flow still accessed the missing `email` attribute, resulting in TypeError.
