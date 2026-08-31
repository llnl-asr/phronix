# Lessons — pallets-flask-4045

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — sqlmigrate transaction wrapping DDL rollback

**2026-08-29** — When wrapping sqlmigrate output in BEGIN/COMMIT, must check can_rollback_ddl in addition to migration.atomic. Without this check, transaction boundaries are incorrectly applied to databases that cannot rollback DDL operations, causing unexpected behavior. The correct condition is: self.output_transaction = migration.atomic and connection.features.can_rollback_ddl.
