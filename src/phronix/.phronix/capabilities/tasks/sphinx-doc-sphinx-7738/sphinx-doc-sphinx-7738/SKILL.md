---
name: sphinx-doc-sphinx-7738
description: The sphinx-doc-sphinx-7738-trailing-underscore-fix subject.
subject: sphinx-doc-sphinx-7738
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix trailing underscore escaping in Napoleon extension |


## Instructions

### I1 — Fix trailing underscore escaping in Napoleon extension

Fix the _escape_args_and_kwargs method in sphinx/ext/napoleon/docstring.py to not escape trailing underscores, matching Sphinx 2.4.3 behavior.

**Change**: In `sphinx/ext/napoleon/docstring.py`, line 322:
- Before: `name = name[:-1] + r'\_'` (strips underscore AND adds backslash escape)
- After: `name = name[:-1]` (just strips the underscore)

This reverts the escaping behavior so that attribute names like `hello_` render as `hello_` in RST output instead of `hello\_` (with visible backslash).

## Rules

## References

- `skill_load(name="sphinx-doc-sphinx-7738-trailing-underscore-fix", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

