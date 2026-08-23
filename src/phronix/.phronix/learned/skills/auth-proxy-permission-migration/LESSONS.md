# Lessons — auth-proxy-permission-migration

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Migration fails for proxy models due to duplicate permission entries

**2026-08-22** — The migration `auth.0011_update_proxy_permissions` attempts to recreate permission entries for proxy models, causing an `IntegrityError` (duplicate key) when the same content_type and codename already exist. Additionally, the patch could not be applied because the test file `tests/auth_tests/test_migrations.py` was missing, preventing verification. The migration's `update_proxy_model_permissions` function does not correctly handle proxy models and needs adjustment to check for existing permissions before creating them, or to target the correct content_type for proxies.
