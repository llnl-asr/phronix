---
name: django-django-14534
description: Correct handling of custom widget IDs in BoundField.id_for_label and BoundWidget.id_for_label, and export BoundWidget.
subject: django-django-14534
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix custom widget ID handling in BoundField and BoundWidget |
| `I2` | Instructions | Fix BoundWidget.id_for_label to respect custom widget IDs |
| `I3` | Instructions | Naming convention for this skill |
| `R1` | Rules | Do not change other widget behavior |




## Instructions

### I1 — Fix custom widget ID handling in BoundField and BoundWidget

Update `django/forms/boundfield.py`:

- In `BoundField.id_for_label`, retrieve the widget's `attrs` dict and return the explicit `id` if present, otherwise fall back to the original auto‑generated ID.
- Add a docstring to `BoundField.id_for_label` explaining the issue and the fix.
- Update `BoundWidget.id_for_label` to first look for an `id` in `self.data.get('attrs', {})` and return it; if not present, use the original `'id_%s_%s' % (self.data['name'], self.data['index'])` fallback.
- Export `BoundWidget` via the module `__all__` tuple so it is publicly available.

These changes ensure custom widget IDs supplied via `attrs` are correctly used for the label's `for` attribute, fixing the failing test `test_iterable_boundfield_select`.

### I2 — Fix BoundWidget.id_for_label to respect custom widget IDs

In `django/forms/boundfield.py`, modify the `id_for_label` property:
```python
@property
def id_for_label(self):
    """Return the widget ID for the <label> ``for`` attribute.
    If the widget data includes an ``attrs`` dict with an ``id`` key, return that value.
    Otherwise fall back to the original implementation based on name and index.
    """
    attrs = self.data.get('attrs', {})
    if attrs and attrs.get('id'):
        return attrs['id']
    return 'id_%s_%s' % (self.data['name'], self.data['index'])
```

### I3 — Naming convention for this skill

Use the slug `django-django-14534` for the skill name; it matches the task identifier and allows later runs to load it directly via `skill_load("django-django-14534")`.

## Rules

### R1 — Do not change other widget behavior

Ensure modifications are limited to `BoundWidget.id_for_label` and do not alter the default ID generation for widgets without explicit `id` attribute.

## References

- `skill_load(name="django-django-14534", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
