---
name: pylint-recursive-ignore-paths-fix
description: The pylint-recursive-ignore-paths-fix subject.
subject: pylint-recursive-ignore-paths-fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I4 |


## Instructions

### I1 — I4

Ensure --recursive flag respects ignore-paths configuration from pyproject.toml/rc files

PROBLEM: The --recursive=y flag in pylint ignores ignore-paths configuration set in pyproject.toml or .pylintrc files. When users configure `ignore-paths = ["^src/gen/.*$"]`, running `pylint --recursive=y src/` still checks files matching that pattern, violating the expected ignore behavior.

FIX: In pylinter.py _discover_files method (line 600-604), ensure self.config.ignore_paths patterns are compiled as regex before being passed to _is_ignored_file. The config's regexp_paths_csv type should produce compiled regex, but verify these patterns reach the _is_ignored_file call during recursive file discovery. Compile ignore-paths into path-matching regex objects consistent with how ignore-patterns handle ignore_list_re, so that ignore-paths = ["^src/gen/.*$"] properly excludes matching files from recursive checking.

## Rules

## References

- `skill_load(name="pylint-recursive-ignore-paths-fix", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

