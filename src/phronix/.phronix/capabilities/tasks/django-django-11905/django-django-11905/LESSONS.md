# Lessons — django-django-11905

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pitfalls

- Raising TypeError directly in ``IsNull.as_sql`` caused ``test_iterator`` to fail because the exception propagated during query iteration teardown. Future fixes must limit the guard to contexts where ``rhs`` is used, not during iteration of unrelated queries.
- A blanket type check may break existing code that passes non‑boolean but truthy values expecting implicit conversion; ensure only ``__isnull`` lookups are targeted.

## Lessons

### L1 — __isnull non-boolean values not rejected

**2026-08-29** — __isnull lookup should reject non-boolean values – agent produced no patch; raising error approach failed
