---
name: flask-blueprint-validation
description: The flask-blueprint-validation subject.
subject: flask-blueprint-validation
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add validation for blueprint name and endpoint names |


## Instructions

### I1 — Add validation for blueprint name and endpoint names

Modify src/flask/blueprints.py:
- In Blueprint.__init__, after calling super().__init__, add a check:
    if "." in name:
        raise ValueError("'name' may not contain a dot '.' character.")
- In Blueprint.add_url_rule, replace the assert checks with explicit ValueError raises:
    if endpoint and "." in endpoint:
        raise ValueError("'endpoint' may not contain a dot '.' character.")
    if view_func and hasattr(view_func, "__name__") and "." in view_func.__name__:
        raise ValueError("'view_func' name may not contain a dot '.' character.")
- Ensure the rest of the method calls self.record as before.
This implements the minimal change to enforce the new constraint.

## Rules

## References
