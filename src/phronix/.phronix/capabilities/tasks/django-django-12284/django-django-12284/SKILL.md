---
name: django-django-12284
description: Fix get_FOO_display handling of inherited choices in Django models.
subject: django-django-12284
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7 Naming |
| `I2` | Instructions | I9 Content |
| `I3` | Instructions | Rule: Preserve existing behavior |
| `I4` | Instructions | Rule: Maintain test suite |
| `I5` | Instructions | Pitfall: MRO walk may miss deeper inheritance |
| `I6` | Instructions | Pitfall: Silent failures |

## Instructions

### I1 — I7 Naming

The skill is named after the task identifier (django-django-12284) to allow direct lookup via skill_load.

### I2 — I9 Content

1. Problem: get_FOO_display does not return the correct label for choices added in a subclass that override the base model's choices.
2. Key idea: Inherited choice values are missing from the field's flatchoices dict; walking the MRO to merge base field choices can populate missing entries.
3. Instructions:
   a. Edit django/db/models/base.py, method _get_FIELD_display.
   b. After building choices_dict, if the value is not present, iterate over base classes in the model's MRO (excluding the class itself).
   c. For each base with _meta, retrieve the same field via base._meta.get_field(field.name).
   d. Merge that field's flatchoices into choices_dict when the value matches.
   e. Return the display value from the updated choices_dict.
4. Constraints:
   - Must not break existing get_FIELD_display behavior for base class choices.
   - Regression tests (31) must remain passing.
   - Avoid altering other model methods.
   - Preserve performance; avoid deep MRO scans beyond immediate base.
5. Pitfalls:
   - The MRO walk may not locate the correct field if field name differs in base.
   - Updating choices_dict without break can mask other bugs.
   - Exception handling must swallow only expected attribute errors.
   - The approach failed to capture inherited choice 'C' because the base field's flatchoices did not include it.
   - Ensure make_hashable is applied consistently.

### I3 — Rule: Preserve existing behavior

Do not modify the handling of values that already exist in choices_dict; the original mapping must stay unchanged.

### I4 — Rule: Maintain test suite

All regression tests must continue to pass after applying the patch.

### I5 — Pitfall: MRO walk may miss deeper inheritance

If the needed choice resides more than one level up, the simple MRO loop may not find it; consider extending the search or revisiting design.

### I6 — Pitfall: Silent failures

Swallowing all exceptions in the MRO loop can hide unrelated errors; limit catch to AttributeError or FieldDoesNotExist.

## Rules
