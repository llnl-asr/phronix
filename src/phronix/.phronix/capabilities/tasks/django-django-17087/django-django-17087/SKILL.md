---
name: django-django-17087
description: The django-django-17087 subject.
subject: django-django-17087
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update Capability default reference in Profile model |
| `I2` | Instructions | Load skill before applying fix |
| `I3` | Instructions | Fix nested class default for ArrayField |
| `I4` | Instructions | Problem: Nested class default values for ArrayField cause migration error |
| `R1` | Rules | Default must reference full nested class path |






## Instructions

### I1 — Update Capability default reference in Profile model

In the `Profile` model, the `ArrayField` for `capabilities` incorrectly used `default=Capability.default`, which resolves to an invalid import path (`appname.models.Capability.default`). Update the default to the fully‑qualified `Profile.Capability.default` to ensure migrations generate the correct path.

```diff
@@
-    capabilities = ArrayField(
-        models.CharField(choices=Capability.choices, max_length=30, blank=True),
-        null=True,
-        default=Capability.default
-    )
+    # Use the fully‑qualified default method from the nested enum.
+    capabilities = ArrayField(
+        models.CharField(choices=Capability.choices, max_length=30, blank=True),
+        null=True,
+        default=Profile.Capability.default
+    )
```

### I2 — Load skill before applying fix

Before making any code edits, ensure the `django-django-17087` skill is loaded with `skill_load("django-django-17087")` so that the appropriate instructions and rules are applied. This prevents attempts from missing the necessary context.

### I3 — Fix nested class default for ArrayField

Edit the `Profile` model's `capabilities` field default to reference the nested class correctly:
```python
class Profile(models.Model):
    class Capability(models.TextChoices):
        BASIC = ("BASIC", "Basic")
        PROFESSIONAL = ("PROFESSIONAL", "Professional")

        @classmethod
        def default(cls) -> list[str]:
            return [cls.BASIC]

    capabilities = ArrayField(
        models.CharField(choices=Capability.choices, max_length=30, blank=True),
        null=True,
        default=Capability.default  # <-- change this line to the following
    )
```
Replace the `default=Capability.default` line with:
```python
        default=Profile.Capability.default
```

### I4 — Problem: Nested class default values for ArrayField cause migration error

When using a nested `TextChoices` class in a Django model, setting `default=Capability.default` for an `ArrayField` results in a migration that references `appname.models.Capability.default` instead of the correct `appname.models.Profile.Capability.default`, causing migration failures.

## Rules

### R1 — Default must reference full nested class path

When assigning a default for an ArrayField that uses a nested TextChoices class, the default callable must be referenced as `Profile.Capability.default`, not just `Capability.default`. This ensures the migration records the correct import path `appname.models.Profile.Capability.default`.

## References

- `skill_load(name="django-django-17087", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

