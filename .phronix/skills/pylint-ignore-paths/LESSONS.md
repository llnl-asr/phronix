# Lessons — pylint-ignore-paths

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Ignore-paths patterns ignored in recursive mode

**2026-08-21** — Symptom: `pylint --recursive=y` ignored `ignore-paths` entries from pyproject.toml, causing unwanted files to be linted.
Root cause: `_is_in_ignore_list_re` used `match`, which anchors at start and didn't handle path separators consistently; `_is_ignored_file` passed absolute paths.
Fix: Normalize element paths to forward slashes, use `search` instead of `match`, and compare against the path relative to the current working directory.
This change ensures ignore-paths patterns correctly filter files during recursive linting.
