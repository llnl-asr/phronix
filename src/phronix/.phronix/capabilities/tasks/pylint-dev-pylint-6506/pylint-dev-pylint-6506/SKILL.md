---
name: pylint-dev-pylint-6506
description: Fix for pylint-dev-pylint-6506 - unrecognized option handling
subject: pylint-dev-pylint-6506
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix unrecognized option handling in pylint run.py |


## Instructions

### I1 — Fix unrecognized option handling in pylint run.py

When handling unrecognized command-line options in pylint, the fix for pylint-dev__pylint-6506 requires two key changes in `pylint/lint/run.py`:

1. **Ensure `sys` is imported at module level**: The `sys` module must be imported at the top of the file (not inside exception handlers). If it's not already present, add `import sys` among the standard library imports.

2. **Print usage message to stderr before exiting**: In the `_UnrecognizedOptionError` exception handler, replace any `import sys` inside the handler with a call to output the usage message to stderr. The correct pattern is:
   ```python
   except _UnrecognizedOptionError:
       # Print usage message to stderr before exiting
       print_usage()  # or however usage is generated
       sys.exit(32)
   ```
   
   If `sys` is needed within the handler, use `global sys` declaration at the top of the handler, or better yet, restructure so `sys` is available from the module scope.

The key principle: never import `sys` inside an exception handler as it creates a local variable that shadows the module-level import. Either import `sys` at the module level, or if you must reference `sys` inside a handler, declare `global sys` explicitly.

Also ensure that the usage message is written to `sys.stderr` (or uses `print(..., file=sys.stderr)`) rather than stdout, so that test expectations for stderr capture are satisfied.

## Rules

## References

- `skill_load(name="pylint-dev-pylint-6506", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

