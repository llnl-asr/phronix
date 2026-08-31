---
name: django-django-15790
description: Fixes duplicate template tag library detection causing E003 errors.
subject: django-django-15790
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Avoid duplicate template tag entries in TEMPLATES settings |
| `I2` | Instructions | Problem description |
| `I3` | Instructions | Avoid duplicate entries in template tag libraries check |
| `R1` | Rules | Do not modify other parts of the check logic |





## Instructions

### I1 — Avoid duplicate template tag entries in TEMPLATES settings

Modify `django/core/checks/templates.py` to only append a template tag library path to `libraries[module_name]` if it is not already present, preventing duplicate entries that cause `E003` errors.

```python
for module_name, module_path in get_template_tag_modules():
    # Avoid adding duplicate entries that are already provided via TEMPLATES settings.
    if module_path not in libraries[module_name]:
        libraries[module_name].append(module_path)
```

### I2 — Problem description

A failing test indicates that the email field handling in the Django project is incorrect when the field name differs from 'email'.

### I3 — Avoid duplicate entries in template tag libraries check

In `django/core/checks/templates.py`, modify the loop that adds template tag modules to skip adding a module path if it is already present in the `libraries` list for that module name.

Replace the original line:
```
libraries[module_name].append(module_path)
```
with:
```
if module_path not in libraries[module_name]:
    libraries[module_name].append(module_path)
```

## Rules

### R1 — Do not modify other parts of the check logic

Only the duplicate‑entry guard should be added; the surrounding logic and other checks must remain unchanged to avoid regression failures.

## References
