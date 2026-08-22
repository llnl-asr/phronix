---
name: software-pylint
description: Fixing pylint's ignore-paths not being respected with --recursive=y flag
subject: software-pylint
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix ignore-paths not working with --recursive=y |
| `R1` | Rules | Normalize paths at EVERY ignore-paths check point |



## Instructions

### I1 — Fix ignore-paths not working with --recursive=y

Apply `os.path.normpath()` to paths in `pylint/lint/expand_modules.py` at TWO locations before checking against `ignore_list_paths_re`:

1. Line ~79: wrap `something` in the initial file loop: `os.path.normpath(something)`
2. Line ~145: wrap `subfilepath` in the recursive directory walk: `os.path.normpath(subfilepath)`

Both are required. Paths like `./src/gen/file.py` won't match patterns like `^src/gen/.*$` without normalization.

## Rules

### R1 — Normalize paths at EVERY ignore-paths check point

In `pylint/lint/expand_modules.py`, both the initial file loop (line ~76-79) AND the recursive directory walk (line ~142-145) pass paths to `_is_ignored_file()` and `_is_in_ignore_list_re()`. The ignore patterns are configured once but applied in multiple places. Missing normalization at any check point causes some ignored paths to leak through.

## References
