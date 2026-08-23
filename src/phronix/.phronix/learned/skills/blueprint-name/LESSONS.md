# Lessons — blueprint-name

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Approach D confirmed twice; pytest collection unusable in this sandbox

**2026-08-22** — 2026-08-22: Approach D (D-combined-init-and-add-url-rule-fix — add ValueError check for "." in name in Blueprint.__init__, plus convert the two dot-checking asserts in Blueprint.add_url_rule to raise ValueError for endpoint and view_func.__name__) passed again: 2/2 target tests, 50/50 regression tests. This is now confirmed twice (attempt-2 and attempt-3) — treat it as the settled fix for this subject, not merely "potential". Local `pytest` collection of tests/test_blueprints.py fails in this sandbox because the installed werkzeug (3.x) is newer than this Flask 2.0 checkout supports (missing werkzeug.urls.url_quote etc., and url_parse triggers a DeprecationWarning treated as an error). This is a pre-existing environment issue, unrelated to the fix — do not chase it or revert a correct change because of it. Verify the fix instead with a direct script that imports Blueprint and calls the three checks/add_url_rule directly, bypassing pytest collection.
