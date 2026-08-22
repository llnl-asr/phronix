---
name: flask-blueprint-validation-edit
description: The flask-blueprint-validation-edit subject.
subject: flask-blueprint-validation-edit
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Edit blueprint validation |


## Instructions

### I1 — Edit blueprint validation

Apply the following modifications to src/flask/blueprints.py:

1. In the __init__ method, after the super().__init__(...), add:
```python
        if "." in name:
            raise ValueError("'name' may not contain a dot '.' character.")
```
This should be placed before `self.name = name`.

2. In the add_url_rule method, replace the assert statements with explicit checks that raise ValueError:
```python
        if endpoint and "." in endpoint:
            raise ValueError("'endpoint' may not contain a dot '.' character.")
        if view_func and hasattr(view_func, "__name__") and "." in view_func.__name__:
            raise ValueError("'view_func' name may not contain a dot '.' character.")
```
Remove the existing `assert` lines (lines with `assert "." not in endpoint` and `assert "." not in view_func.__name__`).

These changes enforce the new constraint on blueprint names, endpoints, and view function names.

## Rules

## References
