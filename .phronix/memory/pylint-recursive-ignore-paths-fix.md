---
name: pylint-recursive-ignore-paths-fix
description: Fix for pylint bug where --recursive=y ignores ignore-paths configuration
metadata:
  type: lesson
---

**Symptom:** When using `pylint --recursive=y`, files matching patterns in `ignore-paths` configuration are still checked, despite being in the ignore list.

**Root Cause:** During recursive directory traversal in `expand_modules.py`, discovered file paths (`subfilepath`) are checked against `ignore-paths` regex patterns WITHOUT being normalized first. This causes patterns written for normalized paths (e.g., `^src/gen/.*$`) to fail matching against unnormalized discovered paths like `./src/gen/file.py` or `src//gen//file.py`.

**Exact Fix:** In `pylint/lint/expand_modules.py`, normalize `subfilepath` using `os.path.normpath()` BEFORE the ignore check at lines 143-146. This ensures all path representations normalize consistently before pattern matching.

**Why:** Python's `os.path.normpath()` converts paths like `./some/path`, `some/path`, and `some//path` to a canonical form `some/path`, making regex pattern matching reliable.

**References:**
- Official fix: https://github.com/pylint-dev/pylint/pull/7080
- Related issue: https://github.com/pylint-dev/pylint/issues/6964
- Python docs: https://docs.python.org/3/library/os.path.html#os.path.normpath
