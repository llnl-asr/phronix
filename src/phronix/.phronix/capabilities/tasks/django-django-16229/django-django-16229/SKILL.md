---
name: django-django-16229
description: The django-django-16229 subject.
subject: django-django-16229
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Disable hidden initial for ArrayField |
| `I3` | Instructions | Steps to solve django__django-16229 |
| `I4` | Instructions | Fix hidden widget value override failure |

## Instructions

### I1 — Problem description

When a ModelForm with an ArrayField that has a callable default (e.g., `default=list`) is used in the Django admin, the inline validation error is bypassed on a second form submission because the hidden input retains the initial value. This causes the inline to be silently dismissed and the field left empty.

### I2 — Disable hidden initial for ArrayField

In `admin.py` add a custom `__init__` to `RelatedModelForm` that sets `self.fields['plop'].show_hidden_initial = False` before calling `super().__init__(*args, **kwargs)`.

### I3 — Steps to solve django__django-16229

When fixing ModelForm fields with callable defaults that don't correctly propagate default values in Django admin inlines with ArrayField:

1. Identify the form field with a callable default (e.g., `default=list` for ArrayField)
2. In the form's `__init__` method, add `show_hidden_initial=False` to the field configuration to prevent the hidden initial input from containing stale/default values
3. This prevents the admin from resetting the field value on repeated submissions when validation errors occur
4. The root cause is that the hidden `<input type="hidden" name="initial-...">` retains the initial value across submissions, and when validation fails and the form is re-submitted, this stale hidden value overwrites the user's input, causing the field to appear empty/unfilled

Note: This fix addresses the symptom where submitting the admin form twice (with an error in between) causes the inline field to become empty/unfilled despite the default being set on the model.

### I4 — Fix hidden widget value override failure

Update `RelatedModelForm.__init__` to also set `self.fields['plop'].widget.show_hidden_initial = False` ensuring the widget respects the overridden value.

```python
class RelatedModelForm(forms.ModelForm):
    class Meta:
        model = RelatedModel
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'plop' in self.fields:
            self.fields['plop'].show_hidden_initial = False
+            # Ensure the widget also disables hidden initial handling
+            self.fields['plop'].widget.show_hidden_initial = False
```

## References
