# Lessons — django-django-13265

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Do not defensive-code the database_forwards method

Pitfall: Attempting to fix by modifying `database_forwards` to handle missing `_order` field was wrong — the real fix is ordering, not defensive coding

### P2 — Autodetector does not auto-detect _order dependency

Pitfall: The autodetector's default ordering places `AlterOrderWithRespectTo` after `AddIndex` because it doesn't recognize the implicit dependency of `AlterOrderWithRespectTo` on the `_order` field

## Lessons
