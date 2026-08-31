---
name: django-django-13658
description: The django-django-13658 subject.
subject: django-django-13658
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem and Key Idea |
| `I2` | Instructions | Instructions to solve it |
| `I3` | Instructions | Constraints and Rules |
| `I4` | Instructions | Pitfalls and Lessons |
| `I5` | Instructions | ManagementUtility CommandParser prog parameter fix |

## Instructions

### I1 — Problem and Key Idea

**Problem:** Django's ManagementUtility uses the program name from `sys.argv[0]` when constructing the `CommandParser`, which fails in embedded environments where `sys.argv[0]` may be `None` or incorrect.
**Key Idea:** Pass the already‑computed `self.prog_name` to `CommandParser` via its `prog` argument, ensuring the usage string reflects the correct program name.

### I2 — Instructions to solve it

1. Open `django/core/management/base.py` in the appropriate location (e.g., `attempt-1/repo/django/core/management/base.py`).
2. Locate the line where `CommandParser` is instantiated:
   ```python
   parser = CommandParser(usage='%(prog)s subcommand [options] [args]', add_help=False, allow_abbrev=False)
   ```
3. Modify this instantiation to pass `prog=self.prog_name`:
   ```python
   parser = CommandParser(
       prog=self.prog_name,
       usage='%(prog)s subcommand [options] [args]',
       add_help=False,
       allow_abbrev=False)
   ```
4. Save the file.

### I3 — Constraints and Rules

- Do not alter any other arguments to `CommandParser`.
- Ensure existing tests that rely on the usage string continue to pass.
- Preserve the behavior of `self.prog_name` assignment logic earlier in `ManagementUtility.__init__`.

### I4 — Pitfalls and Lessons

- Attempting to modify `sys.argv` globally can cause side effects in other parts of Django; instead, use `self.prog_name`.
- Changing only the `usage` string without passing `prog` does not fix the underlying issue because `CommandParser` still derives `prog` from `sys.argv`.
- Ensure the file edited matches the repository version used in tests; editing the wrong copy (e.g., a backup) leads to no effect.

### I5 — ManagementUtility CommandParser prog parameter fix

What problem it solves:
When ManagementUtility instantiates CommandParser in execute() without passing prog=self.prog_name, %(prog)s in usage references sys.argv[0] which can be None in embedded environments, causing incorrect help text.

Key idea:
The pre-computed self.prog_name from ManagementUtility.__init__ is not passed to CommandParser; %(prog)s defaults to sys.argv[0] instead of the computed value.

Instructions to solve it:
File: django/core/management/__init__.py, execute() method, CommandParser constructor
Add prog=self.prog_name parameter so %(prog)s references self.prog_name instead of sys.argv[0].

Constraints:
- Must not regress 181 existing regression tests
- Target test test_xylim_changed_shared must newly pass
- Do not change how self.prog_name is computed in __init__

## References

- `skill_load(name="django-django-13658", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
