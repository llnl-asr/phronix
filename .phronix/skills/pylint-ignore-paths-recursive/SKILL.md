---
name: pylint-ignore-paths-recursive
description: The pylint-ignore-paths-recursive subject.
subject: pylint-ignore-paths-recursive
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Don't append os.sep before passing a path to _is_ignored_file/basename-based matchers |


## Instructions

## Rules

### R1 — Don't append os.sep before passing a path to _is_ignored_file/basename-based matchers

Never call `_is_ignored_file(path + os.sep, ...)` or otherwise append a trailing separator to a directory path before it flows into code that calls `os.path.basename()` on it. `os.path.basename("dir" + os.sep)` returns `""`, silently making the check unmatchable. Why: this exact pattern was tried as the fix for pylint issue "--recursive=y ignores ignore-paths" and produced identical (still-failing) test output because the added check was a no-op. How to apply: when fixing `pylint/lint/pylinter.py::_discover_files` or `pylint/lint/expand_modules.py::_is_ignored_file`, verify any candidate fix actually changes matcher behavior by checking what `os.path.basename` and the regex matchers receive — don't just trust that adding another OR'd condition helps.

## References
