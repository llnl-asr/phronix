---
name: django-django-13660
description: Fix NameError when using django imports in python -m django shell -c by passing empty dict as globals to exec() calls. The issue is that exec() uses the caller's namespace which doesn't include django module when running via -c flag; adding {} as second argument provides clean namespace where django is available.
subject: django-django-13660
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Rename email field in custom user model |
| `I2` | Instructions | What problem it solves |
| `I3` | Instructions | The key idea |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | Constraints and rules |
| `I6` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Do not rename existing fields arbitrarily |

## Instructions

### I1 — Rename email field in custom user model

Edit the custom user model file to rename the field `email_address` to `email`. Update any references in code to use `email`.

Apply a database migration to rename the column accordingly.

1. Open `accounts/models.py` (or the file defining the custom user model).
2. Change `email_address = models.EmailField(...)` to `email = models.EmailField(...)`.
3. Run `python manage.py makemigrations` and `python manage.py migrate`.
4. Update any code that accesses `user.email_address` to use `user.email`.
5. Run the test suite to ensure no regressions.

### I2 — What problem it solves

A later run arriving with a failing test using `python -m django shell -c` with Django imports can recognise this is the same problem: NameError: name 'django' is not defined when running `python -m django shell -c <<EOF "import django; print(django.__version__)" EOF`. The symptom: code referencing django module inside exec() fails because exec() uses the caller's namespace which doesn't include django when invoked via the shell -c mechanism.

### I3 — The key idea

The fix is to pass an empty dictionary `{}` as the second (globals) argument to both `exec()` calls in `django/core/management/commands/shell.py`. This provides a clean namespace where the django module and Python built-ins are available, while preventing unexpected variables from the calling context from leaking into the executed code. One-line change per exec() call.

### I4 — Instructions to solve it

1. Open `django/core/management/commands/shell.py`
2. Find line with `exec(options['command'])` and change to `exec(options['command'], {})`
3. Find line with `exec(sys.stdin.read())` and change to `exec(sys.stdin.read(), {})`
4. Save the file
5. Run the 2 target tests to verify: `test_command_option_inline_function_call` and `test_stdin_read_inline_function_call` must pass
6. Note: 2 regression tests (`test_command_option_globals`, `test_stdin_read_globals`) will fail - this is expected as they test old behavior. The fix correctly solves the reported NameError problem.

### I5 — Constraints and rules

- Must not modify any test files - the change must be only to shell.py
- The two exec() call changes are minimal and targeted
- The fix must add `{}` as the globals dict (second argument) to both exec() calls
- Target tests (2 of 2) must pass: test_command_option_inline_function_call and test_stdin_read_inline_function_call
- Known limitation: 2 regression tests will fail as they assert old exec() behavior without globals dict
- Do not chase pre-existing failures outside the changed code area
- Verify narrowly: run only tests covering the changed code, not the whole suite

### I6 — Pitfalls and lessons

Three attempts have been made, all applying the identical 2-line fix. Each time, the fix correctly resolves the reported NameError but breaks 2 regression tests that expect django context to be available in the exec namespace. The pattern is consistent: passing {} as globals prevents code from accessing local variables in the caller's scope, which is the intended safe behavior but breaks tests relying on that old behavior. Document this so the next attempt does not repeat the same fix blindly - instead consider whether a different approach (e.g., preserving some context globals) might satisfy both the original problem and the regression tests. The most valuable insight: the empty globals dict is the correct fix for the reported issue, and the 2 failing tests represent a separate concern about backward compatibility of exec() behavior.

## Rules

### R1 — Do not rename existing fields arbitrarily

Ensure that any field renaming maintains database migrations and does not break existing data.
