---
name: django-django-11283
description: The django-django-11283 subject.
subject: django-django-11283
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify duplicate auth_permission entries causing migration failure |
| `I2` | Instructions | Key idea: duplicate auth_permission rows must be removed before migration |
| `I3` | Instructions | Create data migration to delete duplicate auth_permission rows |




## Instructions

### I1 — Identify duplicate auth_permission entries causing migration failure

Run the failing test `test_migrate_with_existing_target_permission` to confirm the UNIQUE constraint violation on `auth_permission`.
Check the database for rows with duplicate `(content_type_id, codename)` pairs, especially for the target permission being updated.
If duplicates exist, note their IDs for cleanup.

### I2 — Key idea: duplicate auth_permission rows must be removed before migration

The migration fails because existing `auth_permission` rows with the same `(content_type_id, codename)` already exist. Removing or merging these duplicates resolves the UNIQUE constraint.

### I3 — Create data migration to delete duplicate auth_permission rows

Create a new migration file (e.g., `0012_cleanup_duplicate_permissions.py`) in `django/contrib/auth/migrations/` with:
```python
from django.db import migrations

def cleanup_duplicate_permissions(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    # Find duplicates on (content_type_id, codename)
    from django.db.models import Count
    duplicates = Permission.objects.values('content_type_id', 'codename')\
        .annotate(cnt=Count('id')).filter(cnt__gt=1)
    for dup in duplicates:
        perms = Permission.objects.filter(content_type_id=dup['content_type_id'], codename=dup['codename'])
        # Keep the oldest (or one you decide) and delete the rest
        keep = perms.order_by('id').first()
        perms.exclude(id=keep.id).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
    ]
    operations = [
        migrations.RunPython(cleanup_duplicate_permissions),
    ]
```

## Rules

## References

- `skill_load(name="django-django-11283", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

