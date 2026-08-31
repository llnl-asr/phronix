# Lessons — pytest-dev-pytest-8365

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Attempted to sanitize username by replacing backslashes with underscor

**2026-08-29** — Attempted to sanitize username by replacing backslashes with underscores, but the failing test `test_tmp_path_factory_handles_invalid_dir_characters` expects the string "pytest-of-unknown" in the temporary path. The sanitized username still produced a path like `/tmp/pytest-of-os_______agnostic/pytest-0`, causing the assertion to fail.
