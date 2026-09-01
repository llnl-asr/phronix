# Lessons — django-django-14382

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — django-django-14382

**2026-08-29** — L1: Earlier attempt replaced cgi.parse_header with regex-based parsers across three files for Python 3.13 compatibility — this was necessary but insufficient to fix the trailing slash test. The Python 3.13 compatibility changes and the trailing slash fix are separate concerns.

L2: Simply stripping the trailing slash before `os.path.basename()` was the correct approach, but the implementation must be applied precisely on line 77 of `django/core/management/templates.py`. Partial or incorrect application left the test still failing.

L3: The test `test_trailing_slash_in_target_app_directory_name` expects zero CommandError output. Any `CommandError: '' is not a valid app directory. Please make sure the directory is a valid identifier.` text in the error stream causes the test to fail with `AssertionError: N != 0 : Stream should be empty`.

L4: The fix `os.path.basename(target.rstrip(os.sep))` handles the case where bash tab-completion appends `/` to directory names. Without the `.rstrip(os.sep)`, `os.path.basename('/path/to/directory/')` returns `''` which fails `isidentifier()` validation.
