---
name: django-django-13964
description: The django-django-13964 subject.
subject: django-django-13964
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Detect Docker pull rate limit error |
| `I2` | Instructions | Mitigate rate limit |
| `I3` | Instructions | Re-run the task |
| `I4` | Instructions | Problem Solved |
| `I5` | Instructions | Key Idea |
| `I6` | Instructions | Instructions |
| `R1` | Rules | Do not modify code to work around isolation failures |
| `R2` | Rules | Preserve existing task state |
| `R3` | Rules | Constraints and Rules |

## Instructions

### I1 — Detect Docker pull rate limit error

When a task attempt logs an error containing "You have reached your unauthenticated pull rate limit", recognize this as an environment issue preventing isolation.

### I2 — Mitigate rate limit

Configure Docker to use authenticated pulls or increase rate limit, e.g., by logging into Docker Hub before running attempts.

### I3 — Re-run the task

After fixing Docker authentication, retry the task to allow isolation and tool usage.

### I4 — Problem Solved

Failing test `test_save_fk_after_parent_with_non_numeric_pk_set_on_child` due to foreign‑key caching when assigning a related object with a non‑numeric primary key before the parent is saved.

### I5 — Key Idea

The foreign‑key field does not refresh its cached primary‑key value when the related object’s non‑numeric primary key is set after assignment, causing the parent’s FK to remain empty.

### I6 — Instructions

1. Locate the model where the foreign‑key is defined (e.g., `Order.product`).
2. Before assigning the related object, ensure its primary key is set:
   ```python
   product = Product(sku="foo")
   product.save()
   order = Order()
   order.product = product
   order.save()
   ```
3. If the related object must be created first without a primary key, after setting the PK call `refresh_from_db()` on the related instance before assigning it to the parent:
   ```python
   product = Product()
   product.sku = "foo"
   product.save()
   product.refresh_from_db()
   order = Order()
   order.product = product
   order.save()
   ```
4. Alternatively, assign the foreign‑key directly using the primary‑key value:
   ```python
   order.product_id = "foo"
   order.save()
   ```

## Rules

### R1 — Do not modify code to work around isolation failures

The failure is environment-specific; any code changes are irrelevant and should be avoided.

### R2 — Preserve existing task state

Ensure no changes are committed to the repository before the environment issue is resolved.

### R3 — Constraints and Rules

- Do not modify unrelated models or fields while fixing the FK issue.
- Ensure all existing regression tests (36) continue to pass.
- Preserve the behavior of other foreign‑key relations with numeric primary keys.
- Any change must be compatible with Django’s ORM caching mechanism.
- Avoid re‑introducing the deprecated `cgi` shim; it does not address this problem.

## References

- `skill_load(name="django-django-13964", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
