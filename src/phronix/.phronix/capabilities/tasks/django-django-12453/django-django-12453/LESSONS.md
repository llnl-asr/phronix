# Lessons — django-django-12453

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Import transaction for atomic deserialization

**2026-08-29** — Missing import of transaction caused NameError in deserialize_db_from_string; need to import transaction from django.db.

### L2 — Missing import

**2026-08-29** — Attempt 1 added the transaction block but forgot to import `transaction`, causing a NameError and no test progress.
