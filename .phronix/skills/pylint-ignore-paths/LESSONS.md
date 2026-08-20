# Lessons — pylint-ignore-paths

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — recursive=y bypasses ignore-paths filtering

**2026-08-19** — Symptom: `pylint --recursive=y src/` lints files under paths matched by `ignore-paths` (e.g. `^src/gen/.*$`), even though non-recursive linting respects it.

Root cause: in `pylint/lint/pylinter.py`, the recursive `os.walk` branch (around line 614, inside `_discover_files`/similar) builds the file list with a bare `file.endswith(".py")` generator and never calls `_is_ignored_file`, so `ignore`, `ignore-patterns`, and `ignore-paths` are never applied to recursively-discovered files.

Fix that worked (target test passed, verified): add `and not _is_ignored_file(os.path.join(root, file), self.config.ignore, self.config.ignore_patterns, self.config.ignore_paths)` to that generator's filter. Also in `pylint/lint/expand_modules.py`, `_is_ignored_file` should `os.path.normpath(element)` before matching, since raw walked paths (e.g. `./src/gen/x.py`) can fail regex patterns anchored like `^src/gen/.*$` without normalization.

This is the confirmed correct fix location — the target regression test (recursive + ignore-paths) passed with only these two changes.
