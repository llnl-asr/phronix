---
name: django-django-15320
description: The pytest-all-any-error-messages subject.
subject: django-django-15320
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem it solves |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Fix Subquery.as_sql parentheses and subquery flag handling |
| `I5` | Instructions | Fix all()/any() error messages in pytest assertion rewriting |
| `R1` | Rules | Constraints and rules |
| `R2` | Rules | Set subquery flag |

## Instructions

### I1 — Problem it solves

A failing test because the code assumes the user model always has an `email` attribute, causing a TypeError when a custom user model defines the email field differently.

### I2 — Key idea

The email field may be accessed via a custom getter method (e.g., `get_email_field_name()`) instead of the literal `email` attribute, because custom user models can store the email under a different field name.

### I3 — Instructions to solve it

1. Open `myapp/models.py` (or the relevant model file).
2. Replace direct access to `user.email` with a call to the helper method, e.g.:
   ```python
   email = get_email_field_name(user)
   ```
   where `get_email_field_name` returns the appropriate attribute name for the custom user model.
3. Ensure `get_email_field_name` is defined (e.g., in `utils.py`) to return `user.email_field` if it exists, otherwise `'email'`.
4. Update any imports to include the new helper.
5. Run the test suite; the previously failing test now passes because the code no longer assumes the `email` attribute exists on all user models.

### I4 — Fix Subquery.as_sql parentheses and subquery flag handling

In `django/db/models/expressions.py` modify the template parameters line:
```diff
-        template_params['subquery'] = subquery_sql[1:-1]
+        template_params['subquery'] = subquery_sql
```
Then, ensure the subquery flag is set to True wherever a Subquery instance is used, e.g., after constructing the subquery:
```python
employees_subquery.query.subquery = True
```

### I5 — Fix all()/any() error messages in pytest assertion rewriting

Add `all`/`any` handling to assertrepr_compare in util.py.

## Rules

### R1 — Constraints and rules

* Do not modify other fields of the user model; only change email access.
* Existing tests for other user attributes must continue to pass.
* The helper `get_email_field_name` must return a string and not raise errors for any valid user instance.
* Preserve backward compatibility: if the model already defines `email`, the helper should return `'email'`.
* Do not introduce new dependencies; the helper should reside in a utility module already imported by the app.

### R2 — Set subquery flag

After generating the subquery, ensure the flag is set: `employees_subquery.query.subquery = True`. This must be done wherever a Subquery instance is used before executing the SQL.

## References
