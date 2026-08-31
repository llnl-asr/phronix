---
name: django-django-12453
description: The sympy-issue-atoms subject.
subject: django-django-12453
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints |





## Instructions

### I1 — Problem description

Fix TransactionTestCase.serialized_rollback ordering issue where deserialization saves models without a transaction, causing integrity errors for foreign‑key ordered data.

### I2 — Key idea

Wrap the entire deserialization loop in a single atomic transaction to ensure all objects are saved together, avoiding intermediate integrity errors caused by foreign‑key ordering.

### I3 — Instructions to solve it

1. Edit `django/db/backends/base/creation.py`.
2. Add `transaction` to the imports: `from django.db import router, transaction`.
3. Locate the deserialization loop in `deserialize_db_from_string` (lines ~128‑140).
4. Wrap the loop with `with transaction.atomic(using=self.connection.alias):` and indent the `for obj in serializers.deserialize(...): obj.save()` inside the block.
5. Save the file and run the target test `test_circular_reference`.
6. Ensure the full regression suite still passes.

## Rules

### R1 — Constraints

* The regression suite must remain green.
* Do not alter any import statements other than adding `transaction`.
* Do not change the order of deserialized objects beyond wrapping them in a transaction.
* The fix must be compatible with Django's existing `loaddata` transaction handling.

## References

- `skill_load(name="sympy-issue-atoms", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

