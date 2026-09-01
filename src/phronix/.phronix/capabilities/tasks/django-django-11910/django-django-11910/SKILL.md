---
name: django-django-11910
description: Documents research findings from two failed attempts at fixing Django issue #11910: ForeignKey to_field not updating after RenameField of a PrimaryKey. The skill captures the critical insight that updating remote_field.field_name and field.to_fields in state_forwards() correctly updates in-memory state, but the migration autodetector detects discrepancies at a different pipeline stage, so the extra AlterField operation is still generated.
subject: django-django-11910
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem Symptom |
| `I2` | Instructions | Key One-Sentence Insight |
| `I3` | Instructions | Fix Instructions |

## Instructions

### I1 — Problem Symptom

When a PrimaryKey field is renamed via RenameField migration, ForeignKey to_field references in other models that point to the old field name are not automatically updated to the new name. After running a RenameField migration on a PrimaryKey field, any ForeignKey fields in other models with to_field='old_name' still reference the old field name instead of being updated to the new name.

### I2 — Key One-Sentence Insight

The RenameField.state_forwards() method correctly updates remote_field.field_name and field.to_fields in memory, but the migration autodetector detects to_field discrepancies at a different pipeline stage than state_forwards(), so the fix is invisible to it and it still generates an extra AlterField operation.

### I3 — Fix Instructions

In django/db/migrations/operations/fields.py, within the RenameField.state_forwards() method (around lines 339-354), the current code updates remote_field.field_name and field.to_fields when remote_field.field_name == self.old_name. However, this is necessary but not sufficient. The autodetector runs at a different pipeline stage. To properly fix: after the existing loop that updates field.to_fields (after line 354, after state.reload_model(...)), add logic to iterate through ALL models in state.models and for any ForeignKey field where remote_field.field_name == self.old_name, update remote_field.field_name to self.new_name and update field.to_fields tuple similarly. Example addition after line 354: for (model_app_label, model_name), model_state in state.models.items(): for index, (name, field) in enumerate(model_state.fields): if hasattr(field, 'remote_field') and field.remote_field is not None: remote_field = field.remote_field; if getattr(remote_field, 'field_name', None) == self.old_name: remote_field.field_name = self.new_name; to_fields = getattr(field, 'to_fields', None); if to_fields: field.to_fields = tuple([self.new_name if to_field_name == self.old_name else to_field_name for to_field_name in to_fields])

## Rules
