---
name: django-django-13658
description: The django-django-13658 subject.
subject: django-django-13658
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix CommandParser prog parameter in ManagementUtility.execute |
| `I2` | Instructions | ManagementUtility CommandParser prog parameter fix |
| `I3` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Fix CommandParser prog parameter in ManagementUtility.execute

When instantiating CommandParser in ManagementUtility.execute() (django/core/management/__init__.py, around line 347), always pass prog=self.prog_name as a keyword argument.

The problem: ManagementUtility.__init__ computes self.prog_name from self.argv[0] (with special handling for __main__.py → 'python -m django'), but the CommandParser(...) call did not pass this value. Without the prog parameter, %(prog)s in the usage string defaults to referencing sys.argv[0], which can be None in some embedded environments. This causes the help text to show incorrect or missing program names.

The fix: Add prog=self.prog_name to the CommandParser constructor call so that %(prog)s in the usage string references the pre-computed self.prog_name instead of sys.argv[0].

Changed file: django/core/management/__init__.py

Before:
    parser = CommandParser(usage='%(prog)s subcommand [options] [args]', add_help=False, allow_abbrev=False)

After:
    parser = CommandParser(
        prog=self.prog_name,
        usage='%(prog)s subcommand [options] [args]',
        add_help=False,
        allow_abbrev=False)

### I2 — ManagementUtility CommandParser prog parameter fix

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

### I3 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/core/management/__init__.py b/django/core/management/__init__.py
index 1ba093e51f..4bfe90e857 100755
--- a/django/core/management/__init__.py
+++ b/django/core/management/__init__.py
@@ -344,7 +344,11 @@ class ManagementUtility:
         # Preprocess options to extract --settings and --pythonpath.
         # These options could affect the commands that are available, so they
         # must be processed early.
-        parser = CommandParser(usage='%(prog)s subcommand [options] [args]', add_help=False, allow_abbrev=False)
+        parser = CommandParser(
+            prog=self.prog_name,
+            usage='%(prog)s subcommand [options] [args]',
+            add_help=False,
+            allow_abbrev=False)
         parser.add_argument('--settings')
         parser.add_argument('--pythonpath')
         parser.add_argument('args', nargs='*')  # catch-all
```

## Rules
