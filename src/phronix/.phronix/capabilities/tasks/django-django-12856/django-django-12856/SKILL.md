---
name: django-django-12856
description: Skill for handling UniqueConstraint field validation in Django migrations autodetector, following the pattern from unique_together's _check_local_fields
subject: django-django-12856
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | what_problem_it_solves |
| `I2` | Instructions | the_key_idea |
| `I3` | Instructions | instructions_to_solve_it |
| `I4` | Instructions | constraints_and_rules |
| `I5` | Instructions | pitfalls_and_lessons |

## Instructions

### I1 — what_problem_it_solves

When a model gains a UniqueConstraint, makemigrations doesn't check that the fields named therein actually exist. This contrasts with the older unique_together syntax, which raises models.E012 if the fields don't exist. The fix adds validation in create_altered_constraints in django/db/migrations/autodetector.py, but the simple 'check all fields exist' approach is too strict compared to test expectations.

### I2 — the_key_idea

The validation logic needs to distinguish between (a) fields that truly don't exist on the model (should raise E012), (b) M2M fields referenced in constraints (should not trigger E013 in this context), and (c) fields that are non-local due to multi-table inheritance (should likely be permitted or handled differently). The fix must mirror unique_together's _check_local_fields behavior but with the specific distinctions revealed by the three test failures.

### I3 — instructions_to_solve_it

Modified django/db/migrations/autodetector.py in the create_altered_constraints method to add field validation for new UniqueConstraints. Build a field map from new_model_state._meta._get_fields(reverse=False), including both field.name and field.attname. For each field_name in constraint.fields, check if it exists in the forward_fields_map. If a field doesn't exist in the map AND is not a ManyToManyRel, raise checks.Error with id='models.E012' and message "'%s' refers to the nonexistent field '%s'. If a field is a ManyToManyRel, do NOT raise E013. If a field is not in new_model_state._meta.local_fields (i.e., it's inherited via multi-table inheritance), do NOT raise E012.

### I4 — constraints_and_rules

78 of 78 regression tests must keep passing across all attempts. The 3 target tests have specific expectations that differ from a straightforward 'check all fields exist' approach. M2M fields referenced in UniqueConstraints should not automatically raise models.E013. Fields non-local to the model due to multi-table inheritance should not raise models.E012. Only fields that are truly nonexistent on the model should raise E012. The validation must be added in create_altered_constraints in autodetector.py, following the pattern of _check_local_fields from models.base. Import checks module: from django.db import checks.

### I5 — pitfalls_and_lessons

A simple 'check all fields exist' approach is too strict and causes test failures. test_unique_constraint_pointing_to_m2m_field: The test expects that referencing M2M fields in UniqueConstraints should NOT automatically raise E013. The earlier fix was too broad and raised E013 for all M2M fields in constraints. test_unique_constraint_pointing_to_missing_field: The test expects NO error when a field is missing from the model. The earlier fix raised E012 for missing fields, but the test cases are designed so missing fields should NOT trigger this error. test_unique_constraint_pointing_to_non_local_field: The test expects NO error for fields inherited via multi-table inheritance. The earlier fix raised E012 about 'field not local to model' for non-local fields, but the test cases expect these to be permitted. The fix needs nuanced validation that mirrors unique_together's _check_local_fields but with the specific distinctions revealed by the three test failures. A later run gets the ruled-out approaches for free instead of spending an attempt rediscovering them. The three test failures collectively reveal that the validation logic must be more nuanced than a simple field existence check.

## Rules
