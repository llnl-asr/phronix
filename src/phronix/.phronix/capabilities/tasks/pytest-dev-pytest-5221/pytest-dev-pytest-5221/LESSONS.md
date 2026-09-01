# Lessons — pytest-dev-pytest-5221

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Incorrect fixture scope formatting

**2026-08-27** — The previous attempt added fixture scope in the output using `(scope: ...)` format, causing test `TestShowFixtures.test_show_fixtures` to fail with a mismatch expecting the original `[scope]` formatting. The diff showed the added lines and the test output did not contain `tmpdir_factory [session]` as expected, leading to a `nomatch` failure.
