---
name: django-django-16229
description: The django-django-16229 subject.
subject: django-django-16229
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix hidden widget value override failure |


## Instructions

### I1 — Fix hidden widget value override failure

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

## Rules

## References
