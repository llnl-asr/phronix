---
name: django-django-13925-w042-fix
description: Fix Django W042 warning incorrectly raised on models inheriting from parents with manually specified primary keys. The issue is that ModelBase.__new__ creates parent_link OneToOneFields with auto_created=True unconditionally, without checking if the parent has an explicitly defined primary key.
subject: django-w042-model-inheritance-fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I1: Fix auto_created flag propagation in ModelBase.__new__ |


## Instructions

### I1 — I1: Fix auto_created flag propagation in ModelBase.__new__

When creating a OneToOneField parent_link in ModelBase.__new__ (django/db/models/base.py lines 243-249), conditionally set the auto_created parameter based on whether the parent class has an explicitly defined primary key:

1. After creating the OneToOneField (line 243-249), check if the parent has a manually specified primary key by examining parent._meta.pk.auto_created
2. If parent._meta.pk.auto_created is False (parent has manually specified PK), set the field's auto_created parameter to False
3. If parent._meta.pk.auto_created is True (parent has Django-generated PK), keep auto_created as True

The exact code change at django/db/models/base.py lines 243-249:

Before:
    field = OneToOneField(
        base,
        on_delete=CASCADE,
        name=attr_name,
        auto_created=True,
        parent_link=True,
    )

After:
    # Only mark the parent link as auto-created if the parent's PK was
    # also auto-created. If the parent has a manually specified primary key,
    # the child should not mark the inherited PK as auto-created either.
    parent_auto_created = getattr(base._meta.pk, 'auto_created', True)
    field = OneToOneField(
        base,
        on_delete=CASCADE,
        name=attr_name,
        auto_created=parent_auto_created,
        parent_link=True,
    )

## Rules

## References
