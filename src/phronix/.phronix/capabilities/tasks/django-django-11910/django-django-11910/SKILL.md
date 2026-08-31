---
name: django-django-11910
description: Documents research findings from two failed attempts at fixing Django issue #11910: ForeignKey to_field not updating after RenameField of a PrimaryKey. The skill captures the critical insight that updating remote_field.field_name and field.to_fields in state_forwards() correctly updates in-memory state, but the migration autodetector detects discrepancies at a different pipeline stage, so the extra AlterField operation is still generated.
subject: django-django-11910
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem it solves |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Steps |
| `I4` | Instructions | Constraints |
| `I5` | Instructions | Pitfalls |
| `I6` | Instructions | Instructions to solve it |
| `I7` | Instructions | Problem Symptom |
| `I8` | Instructions | Key One-Sentence Insight |
| `I9` | Instructions | Fix Instructions |
| `R1` | Rules | Constraints and rules |

## Instructions

### I1 — Problem it solves

Fix failing test `test_rename_referenced_primary_key` caused by a ForeignKey's `to_field` still referencing the old primary key name after the primary key field was renamed.

### I2 — Key Idea

Update the migration to rename the primary key field and adjust the foreign key's to_field to the new name.

### I3 — Steps

1. Create a new migration file `app1/migrations/0002_auto.py`.
2. Use `migrations.RenameField` to rename `field_wrong` to `field_fixed` on `ModelA`.
3. Use `migrations.AlterField` to update `ModelB`'s foreign key to point to `ModelA` with `to_field='field_fixed'`.

### I4 — Constraints

All existing tests must continue to pass; only the failing target test `test_rename_referenced_primary_key` should be fixed.

### I5 — Pitfalls

Do not forget to update the `to_field` in the foreign key; otherwise the migration will still reference the old field and fail.

### I6 — Instructions to solve it

1. Create a new migration file `app1/migrations/0002_auto.py`.
2. In the migration, add a `RenameField` operation to rename `field_wrong` to `field_fixed` on `ModelA`.
3. Add an `AlterField` operation on `ModelB` to update the foreign key:
   ```python
   migrations.AlterField(
       model_name='modelb',
       name='modela',
       field=models.ForeignKey(
           on_delete=django.db.models.deletion.CASCADE,
           to='app1.ModelA',
           to_field='field_fixed',
           blank=True,
           null=True,
       ),
   )
   ```
4. Run `python manage.py migrate app1 0002_auto` to apply the migration.
5. Execute the target test `test_rename_referenced_primary_key` to confirm it passes.
6. Ensure the full test suite still passes.

### I7 — Problem Symptom

When a PrimaryKey field is renamed via RenameField migration, ForeignKey to_field references in other models that point to the old field name are not automatically updated to the new name. After running a RenameField migration on a PrimaryKey field, any ForeignKey fields in other models with to_field='old_name' still reference the old field name instead of being updated to the new name.

### I8 — Key One-Sentence Insight

The RenameField.state_forwards() method correctly updates remote_field.field_name and field.to_fields in memory, but the migration autodetector detects to_field discrepancies at a different pipeline stage than state_forwards(), so the fix is invisible to it and it still generates an extra AlterField operation.

### I9 — Fix Instructions

In django/db/migrations/operations/fields.py, within the RenameField.state_forwards() method (around lines 339-354), the current code updates remote_field.field_name and field.to_fields when remote_field.field_name == self.old_name. However, this is necessary but not sufficient. The autodetector runs at a different pipeline stage. To properly fix: after the existing loop that updates field.to_fields (after line 354, after state.reload_model(...)), add logic to iterate through ALL models in state.models and for any ForeignKey field where remote_field.field_name == self.old_name, update remote_field.field_name to self.new_name and update field.to_fields tuple similarly. Example addition after line 354: for (model_app_label, model_name), model_state in state.models.items(): for index, (name, field) in enumerate(model_state.fields): if hasattr(field, 'remote_field') and field.remote_field is not None: remote_field = field.remote_field; if getattr(remote_field, 'field_name', None) == self.old_name: remote_field.field_name = self.new_name; to_fields = getattr(field, 'to_fields', None); if to_fields: field.to_fields = tuple([self.new_name if to_field_name == self.old_name else to_field_name for to_field_name in to_fields])

## Rules

### R1 — Constraints and rules

- All existing regression tests (110) must continue to pass.
- The migration must not alter any other fields or models.
- The foreign key name in ModelB remains `modela` (only `to_field` changes).
- The migration should be reversible by Django's migration system.
- Do not change the `on_delete` behavior.

## References

- `skill_load(name="django-django-11910", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
