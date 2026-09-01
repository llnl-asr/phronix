---
name: django-django-15202
description: The django-django-15202 subject.
subject: django-django-15202
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem Solved |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Instructions to Solve It |
| `R1` | Rules | Constraints |





## Instructions

### I1 — Problem Solved

URLField raises a TypeError (None hostname) during validation, causing target tests `test_urlfield_clean_invalid` and `test_urlfield_clean_not_required` to error instead of returning a ValidationError.

### I2 — Key Idea

The validation error originates from `URLValidator` raising a `TypeError` when the hostname is `None`; handling this in `clean` is too late because validation occurs earlier in the field pipeline.

### I3 — Instructions to Solve It

1. Edit `django/forms/fields.py` at the `URLField` class.
2. Add a custom validator that safely handles `None` hostnames before `URLValidator` runs.
   ```python
   from django.core.exceptions import ValidationError
   from django.core.validators import URLValidator

   class SafeURLValidator(URLValidator):
       def __call__(self, value):
           try:
               super().__call__(value)
           except TypeError:
               raise ValidationError(self.message, code=self.code)
   ```
3. In the `URLField` definition, set `default_validators = [SafeURLValidator()]`.
4. Remove the previously added `clean` method override (it is no longer needed).
5. Run the test suite; the target tests `test_urlfield_clean_invalid` and `test_urlfield_clean_not_required` should now pass.

## Rules

### R1 — Constraints

- Regression tests (6) must continue to pass.
- Do not alter other field validators or change existing field behavior beyond URL validation.
- Preserve the original error messages for invalid URLs.
- Ensure the custom validator is used only for URLField to avoid side effects on other fields.

## References

- `skill_load(name="django-django-15202", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

