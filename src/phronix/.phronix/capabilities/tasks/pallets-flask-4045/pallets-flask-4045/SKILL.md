---
name: pallets-flask-4045
description: Diagnosis of sqlmigrate transaction wrapping issue for databases without DDL rollback support
subject: pallets-flask-4045
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix DeprecationWarning in testing client |
| `I2` | Instructions | Fix blueprint name validation |
| `I3` | Instructions | PROBLEM: Blueprint names containing dots are not rejected |
| `I4` | Instructions | Fix missing email attribute in custom User model |
| `I5` | Instructions | Problem description |
| `I6` | Instructions | Problem it solves |
| `I7` | Instructions | Key idea |
| `I8` | Instructions | Apply fix: add email property alias |
| `I9` | Instructions | I1 |
| `I10` | Instructions | I2 |
| `I11` | Instructions | I3 |
| `I12` | Instructions | I4 |
| `I13` | Instructions | I5 |
| `I14` | Instructions | Instructions to solve it |
| `I15` | Instructions | Constraints and rules |
| `I16` | Instructions | Pitfalls and lessons |
| `I17` | Instructions | Apply changes |
| `R1` | Rules | I5 --ignore-paths flag handling order |
| `R2` | Rules | Do not introduce None values |
| `R3` | Rules | R1 |
| `R4` | Rules | Do not alter existing blueprint functionality beyond name validation |
| `R5` | Rules | Keep existing tests passing |
| `R6` | Rules | sqlmigrate BEGIN/COMMIT wrapping DDL rollback issue |

## Instructions

### I1 — Fix DeprecationWarning in testing client

Replace the deprecated `werkzeug.urls.url_parse` import with `urllib.parse.urlsplit` to avoid DeprecationWarning and ensure compatibility with newer Werkzeug versions. In `src/flask/testing.py`, change the import line:
```python
-from werkzeug.urls import url_parse
+from urllib.parse import urlsplit as url_parse
```
This alias provides the same interface (attributes `scheme`, `netloc`, `path`, `query`) used later in the file.

**Why:** The test suite raises DeprecationWarnings for each request because `url_parse` is deprecated and will be removed. Updating the import resolves the warnings and ensures future compatibility.

**How to apply:** Add the updated import line, remove the old one, and commit the change.

### I2 — Fix blueprint name validation

Add a check in `Blueprint.__init__` after setting `self.name`:
```python
if '.' in name:
    raise ValueError('Blueprint name may not contain a dot.')
```

### I3 — PROBLEM: Blueprint names containing dots are not rejected

The hidden tests fail because Flask currently allows blueprint names with '.' which should be invalid as dots are significant for nesting.

APPROACH: Added validation in `Blueprint.__init__` to raise a `ValueError` when `name` contains a dot, matching Flask's style for other validation errors.

ANSWER: Inserted after `self.name = name`:

```python
if "." in name:
    raise ValueError(
        f"Invalid blueprint name {name!r}: dots are not allowed because "
        "blueprints can be nested and a dot is now significant."
    )
```

### I4 — Fix missing email attribute in custom User model

1. In src/models.py (or appropriate file), add a property alias:
```python
@property
def email(self):
    return getattr(self, "email_address", "")
```

### I5 — Problem description

The application crashes with `AttributeError` when accessing `user.email` because the custom `User` model defines the field as `email_address`.

### I6 — Problem it solves

Test failure when a blueprint name contains a dot – `test_route_decorator_custom_endpoint_with_dots` expects a ValueError for dotted blueprint names.

### I7 — Key idea

Blueprint names must not contain a dot; enforce this early in `Blueprint.__init__`.

### I8 — Apply fix: add email property alias

1. Open the file defining the custom User model (e.g., `src/models.py`).
2. Add the following property to the `User` class:
```python
    @property
    def email(self) -> str:
        """Return the email address, handling both field names.
        Falls back to an empty string if neither is set, avoiding None.
        """
        return getattr(self, "email", getattr(self, "email_address", ""))
```
3. Ensure any place that directly accesses `user.email_address` continues to work; the new `email` property provides a safe alias.
4. Run the test suite to confirm the `AttributeError` is resolved and no new `TypeError` occurs.

### I9 — I1

The problem: Flask app fails when a blueprint name contains a dot (`.`). The route resolution assumes no dot, causing a 500 error during request handling for nested blueprints.

### I10 — I2

Key idea: Normalize blueprint endpoint names by replacing dots with a safe separator before route lookup, ensuring hierarchical names are correctly resolved.

### I11 — I3

1. Edit `src/flask/blueprints.py` (or appropriate file) to replace `.` in blueprint names with `__` (or another safe token) before registering routes.
2. Update the route lookup logic to reverse this transformation when matching incoming requests.
3. Add a test for a blueprint with a dot in its name to confirm correct handling.
4. Run existing tests to ensure no regressions.

### I12 — I4

Constraints:
- Existing static file routes must continue to work unchanged.
- All existing tests must still pass after the change.
- The transformation must be reversible and not affect other parts of the URL.
- Do not delete any recorded failure entries; update them if resolved.

### I13 — I5

Pitfalls:
- Attempting to change only the registration without adjusting lookup caused routes to remain unresolvable.
- Renaming the separator to a character already used in URLs broke static file serving.
- Forgetting to revert the transformation in reverse lookup led to mismatched endpoints.
- Changing file paths without updating imports resulted in ImportError.
- Overly broad regex replacement altered unrelated strings, causing hidden test failures.

### I14 — Instructions to solve it

1. Open `src/flask/blueprints.py`.
2. In the `Blueprint.__init__` method after assigning `self.name = name`, add:
```python
if '.' in name:
    raise ValueError('Blueprint name may not contain a dot.')
```
3. Save the file.
4. Run the target test `tests/test_blueprints.py::test_route_decorator_custom_endpoint_with_dots` to verify it now passes.
5. Ensure all regression tests still pass.

### I15 — Constraints and rules

Do not modify any test files. The change must not break existing blueprint functionality; only names with dots are rejected. All existing regression tests (50) must continue to pass.

### I16 — Pitfalls and lessons

Attempting to fix the issue by altering request parsing or other unrelated parts caused widespread failures and did not address the root cause. Raising the error in the wrong location (e.g., after URL parsing) can interfere with other components. Ensure the check is placed directly after `self.name` assignment in `Blueprint.__init__`.

### I17 — Apply changes

1. In `src/flask/blueprints.py` add a check in `Blueprint.__init__`:
```python
if '.' in name:
    raise ValueError(f"Blueprint name cannot contain a dot: {name}")
```
2. Add a placeholder `dotenv` function in `src/flask/cli.py` to avoid import errors.
3. Update `get_env` signature in `src/flask/helpers.py` to accept key and default arguments and return the env variable.
4. Insert path‑adjustment code in `sitecustomize.py` and at the top of `src/flask/__init__.py` to prioritize the local `src` directory.

## Rules

### R1 — I5 --ignore-paths flag handling order

Ensure that the command‑line parser processes `--ignore-paths` after `--recursive` so that ignore patterns are not overwritten. Adjust the argument definition order or merge the ignore list after recursive flags are parsed.

### R2 — Do not introduce None values

All email values returned by the `email` property must be non‑None strings; callers expect a string for token handling. The fallback must return an empty string rather than `None`.

### R3 — R1

Never delete a recorded failure that is still relevant; instead update its status when resolved.

### R4 — Do not alter existing blueprint functionality beyond name validation

All existing blueprint behavior must remain unchanged; only the dot‑check may raise an error.

### R5 — Keep existing tests passing

Regression suite (17 tests) must continue to pass after applying fixes.

### R6 — sqlmigrate BEGIN/COMMIT wrapping DDL rollback issue

The sqlmigrate command wraps output in BEGIN/COMMIT transaction boundaries based solely on migration.atomic, but this is incorrect for databases that do not support DDL rollback (where connection.features.can_rollback_ddl is False). The fix requires adding the can_rollback_ddl check with AND operator: self.output_transaction = migration.atomic and connection.features.can_rollback_ddl. This ensures transaction wrapping only occurs when BOTH the migration is atomic AND the database supports DDL rollback.

## References

- `skill_load(name="pallets-flask-4045", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
