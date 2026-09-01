---
name: django-django-12589
description: The django-django-12589 subject.
subject: django-django-12589
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | problem_description |
| `I2` | Instructions | key_idea |
| `I3` | Instructions | constraints |
| `I4` | Instructions | pitfalls |
| `R1` | Rules | rules |






## Instructions

### I1 — problem_description

Django 3.0.4 raises ProgrammingError: column reference "status" is ambiguous when evaluating queries with Subquery.values("status") on ManyToMany through intermediate model. Works in Django 2.2.11.

### I2 — key_idea

Subquery.get_group_by_cols() must return [Ref(alias, self)] without adding external_cols when the subquery's own source expressions reference columns that the outer query also groups by, preventing column ambiguity.

### I3 — constraints

- Do NOT change the base Expression.get_group_by_cols() method behavior
- The fix must only affect Subquery.get_group_by_cols()
- Must not break the 64 tests that currently pass (regression-free)
- The target test test_aggregation_subquery_annotation_values_collision must pass (0/1 → 1/1)
- Must not introduce the 2 regression failures: test_group_by_exists_annotation and test_group_by_subquery_annotation
- The fix should be minimal - preferably a 1-line or 2-line change to the condition
- Do NOT add all external_cols unconditionally when alias is provided (this was the mistake in attempt-2)

### I4 — pitfalls

- Unconditionally adding external_cols when alias is provided and any external col is possibly_multivalued (attempt-2) did NOT fix target test and introduced 2 regression failures
- The fix was too broad - adding external_cols affected test cases that previously passed
- No alternative approach was trialed yet - subsequent phase should explore different fix strategies
- The 12-minute research inefficiency delta from re-exploring already-mapped territory should be avoided
- Key takeaway: condition for adding external_cols must be narrow enough to only apply when truly needed

## Rules

### R1 — rules

- The fix must only modify Subquery.get_group_by_cols() in django/db/models/expressions.py
- The fix must preserve backward compatibility with Django 2.2.11 behavior for queries that already work
- The fix must make the target test pass: test_aggregation_subquery_annotation_values_collision
- The fix must not cause regressions in test_group_by_exists_annotation or test_group_by_subquery_annotation
- The fix should be minimal - change the condition, not the entire method logic
- Do not add external_cols when the subquery's own source expressions already reference the grouped column

## References
