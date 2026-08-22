# Lessons — normalize-ignore-paths

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — ignore-paths ignored with recursive flag

**2026-08-21** — Symptom: `pylint --recursive=y` ignores `ignore-paths` patterns defined in pyproject.toml. Root cause: The recursive file discovery in pylint does not apply ignore-paths filters during traversal, so files matching ignore patterns are still linted. Exact fix: Apply ignore-paths filtering after normalizing discovered file paths, e.g., add `element = os.path.normpath(element)` before checking ignore patterns in `_is_ignored_file` (see PR #7080).
