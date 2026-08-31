---
name: django-django-16820-solution
description: Solution for task django-16820 fixing deprecation handling and widget import.
subject: django-django-16820-solution
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7 Fix BoundWidget import and id_for_label |


## Instructions

### I1 — I7 Fix BoundWidget import and id_for_label

In `django/forms/widgets.py` import `Widget` before defining `BoundWidget` to avoid NameError. Then implement `BoundWidget.id_for_label` to return the widget's ``id`` when present:
```python
class BoundWidget:
    def __init__(self, widget, name, value, attrs=None, bound=False):
        self.widget = widget
        self.name = name
        self.value = value
        self.attrs = attrs or {}
        self.is_hidden = getattr(widget, 'is_hidden', False)
        self.bound = bound
    def id_for_label(self):
        # Use explicit id if provided in attrs;
        # otherwise fallback to default widget method.
        return self.attrs.get('id') or getattr(self.widget, 'id_for_label', lambda *a: None)(self.name, self.value, self.attrs)
```

## Rules

## References
