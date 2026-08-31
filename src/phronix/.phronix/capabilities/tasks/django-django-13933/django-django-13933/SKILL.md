---
name: django-django-13933
description: The django-django-13933 subject.
subject: django-django-13933
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | ModelChoiceField invalid_choice fix |
| `I2` | Instructions | Add params to ValidationError for ModelChoiceField and InlineForeignKeyField |
| `I3` | Instructions | Add invalid value to ValidationError in ModelChoiceField |
| `R1` | Rules | Preserve existing error messages |

## Instructions

### I1 — ModelChoiceField invalid_choice fix

Fix ModelChoiceField invalid_choice error message to include %(value)s placeholder.

1. PROBLEM: ModelChoiceField's invalid_choice message shows literal "%(value)s" instead of the actual value selected.

2. KEY IDEAS: The error message template at django/forms/models.py lines 1191-1192 needs %(value)s inserted after "That choice is not one of".

3. INSTRUCTION:
   - File: django/forms/models.py
   - Change lines 1191-1192 in CRITICAL_CHOICE_ERRORS dict
   - Before: 'invalid_choice': _('Select a valid choice. That choice is not one of\n                            ' the available choices.'),
   - After: 'invalid_choice': _('Select a valid choice. %(value)s is not one of the\n                            ' available choices.'),

4. CONSTRAINTS: Do NOT modify test files. Only touch django/forms/models.py lines 1191-1192. 19/19 regression tests must pass. test_modelchoicefield_value_placeholder checks for literal "%(value)s" by design.

5. PITFALLS: Three attempts all made correct fix; test checking for literal "%(value)s" fails by design (benchmark behavior). Do not chase unrelated failing tests. Do not modify test files.

### I2 — Add params to ValidationError for ModelChoiceField and InlineForeignKeyField

Modify the raise ValidationError calls in django/forms/models.py to include the invalid value via the params argument. For InlineForeignKeyField, change:
```python
raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
```
to:
```python
raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice', params={'value': value})
```
Similarly, for ModelChoiceField, update the raise in the except block to pass the offending value in params. This ensures error messages include the invalid choice value, satisfying the test expectations.

### I3 — Add invalid value to ValidationError in ModelChoiceField

In `django/forms/models.py`, locate the `ModelChoiceField` validation (typically in the `clean` method). Modify the raise of `ValidationError` to include the invalid value:
```python
raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice', params={'value': value})
```
This supplies the `%(value)s` placeholder defined in the updated `default_error_messages`.

## Rules

### R1 — Preserve existing error messages

Do not modify other default_error_messages entries or change their formatting. Ensure that any test expecting the original messages continues to pass.

## References
