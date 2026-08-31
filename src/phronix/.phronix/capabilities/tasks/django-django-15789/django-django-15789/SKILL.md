---
name: django-django-15789
description: Support custom JSON encoder in json_script
subject: django-django-15789
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |

## Instructions

### I1 — What problem it solves

Allow callers of django.utils.html.json_script to provide a custom JSON encoder, enabling serialization of custom data types.

### I2 — Key idea

Add optional encoder argument defaulting to DjangoJSONEncoder and use it in json.dumps.

### I3 — Instructions to solve it

1. Edit django/utils/html.py.
2. Change function signature to `def json_script(value, element_id=None, encoder=None):`.
3. Inside, set `encoder_cls = encoder if encoder is not None else DjangoJSONEncoder`.
4. Replace json.dumps call with `json.dumps(value, cls=encoder_cls)`.
5. Preserve existing behavior by default.

### I4 — Constraints and rules

- Do not alter other parts of json_script.
- Ensure all existing tests continue to pass.
- Default encoder must be DjangoJSONEncoder when encoder is None.

### I5 — Pitfalls and lessons

- Adding a parameter without default breaks callers; provide default None.
- Ensure the import of DjangoJSONEncoder remains.
- Verify that custom encoder class is compatible with json.dumps cls parameter.

## Rules
