# Lessons — django-django-16400

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — The test `test_set_permissions_fk_to_using_parameter` failed because t

**2026-08-29** — The test `test_set_permissions_fk_to_using_parameter` failed because the router raised `InvalidTenantException` when `using='other'` was passed during permission creation. The router did not respect the explicit `using` hint, causing a ValueError in the permission management command.
