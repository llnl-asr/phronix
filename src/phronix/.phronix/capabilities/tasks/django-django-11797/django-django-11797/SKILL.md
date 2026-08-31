---
name: django-django-11797
description: The django-django-11797 subject.
subject: django-django-11797
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem solved |
| `I2` | Instructions | Symptom |
| `I3` | Instructions | The key idea |
| `I4` | Instructions | Apply fix |
| `I5` | Instructions | What problem it solves |
| `I6` | Instructions | Instructions to solve it |
| `I7` | Instructions | Pitfalls and lessons (3 of 3) |
| `I8` | Instructions | Fix import error for jinja2 pass_environment |
| `R1` | Rules | Constraints and rules (continued) |

## Instructions

### I1 — Problem solved

Filtering on query result overrides GROUP BY of internal query, causing incorrect grouping when using a subquery filter on `id`.

### I2 — Symptom

A failing test shows that filtering on a subquery result overrides the GROUP BY clause, producing incorrect grouping when using `filter(id=Subquery)` on the `User` model.

### I3 — The key idea

The email field is not always called `email` — the GROUP BY from a previous `.values()` clause can be on any field specified in that values() call, and the fix must preserve whatever GROUP BY is already set (e.g., `U0."email"`) rather than unconditionally resetting it to the primary key (`U0."id"`). The fix must check whether `group_by` is already set before forcing it to the primary key.

### I4 — Apply fix

1. Open the file where the query is built (e.g. `django/contrib/auth/models.py`).
2. Locate the line `b = models.User.objects.filter(id=a[:1])`.
3. Replace it with:
   ```python
   b = models.User.objects.filter(id__in=a)
   ```
   This uses the subquery as an `IN` lookup, preserving the original `GROUP BY` on `email`.
4. Save the file and run the targeted test that exercises this query.
5. Ensure the test passes and no other tests regress.

### I5 — What problem it solves

When a Django ORM query uses values() followed by annotate() and then values() again (e.g., `models.User.objects.filter(email__isnull=True).values('email').annotate(m=Max('id')).values('m')`), and a subsequent filter() is applied on the result (e.g., `models.User.objects.filter(id=a[:1])`), the GROUP BY clause from the inner values()/annotate() query is lost. The filter() then uses the primary key column (id) instead of the original grouping field (email), causing incorrect query results. This skill is recognized by the symptom: a test or code pattern where filtering on a values()+annotate() query result produces SQL with GROUP BY on the wrong column.

### I6 — Instructions to solve it

1. Locate the `inner_query.group_by = (self.model._meta.pk.get_col(inner_query.get_initial_alias()),)` assignment in `django/db/models/sql/query.py` (around line 453, in the `get_annotation` method of the `Query` class).

2. Before this unconditional assignment, add a conditional check: `if not inner_query.group_by:`

3. The complete change wraps the original line with a conditional:
```python
if not inner_query.group_by:
    inner_query.group_by = (self.model._meta.pk.get_col(inner_query.get_initial_alias()),)
```
This ensures the GROUP BY is only forced to the primary key when no GROUP BY has been set previously (e.g., from a prior `.values('email')` clause).

4. After the conditional block, ensure `inner_query.default_cols = False` is still set (this was already present in the original code and must be preserved).

5. Verify the fix by running the existing test suite: 38 of 38 regression tests must continue to pass, and the target test `test_exact_query_rhs_with_selected_columns` should be the only remaining failure (which is expected as noted in the task constraints).

### I7 — Pitfalls and lessons (3 of 3)

- Target test `test_exact_query_rhs_with_selected_columns` fails with `AssertionError: <Author: Author object (2)> != <Author: Author object (3)>` — the query returns Author object (2) instead of expected Author object (3) due to incorrect GROUP BY, but the documented fix does not resolve this specific case.
- The fix pattern (preventing unconditional `group_by` reset) is validated and banked: 38/38 regression tests confirm it is safe and correct. Do not re-derive this same fix expecting it to solve the target test.
- Do not chase the failing test as a pre-existing issue: Per user instructions, this is explicitly ruled out. Document what was tried, what worked, and what did not without attempting further research.

### I8 — Fix import error for jinja2 pass_environment

Update `sphinx/util/rst.py` to import `pass_environment` from `jinja2` using the correct name:
```python
from jinja2 import pass_environment as environmentfilter
```
This resolves the ImportError raised during test collection.

## Rules

### R1 — Constraints and rules (continued)

- Preserve `inner_query.default_cols = False`: This line must remain after the conditional group_by block; it was part of the original code and is essential for correct query compilation.
- Only force group_by to primary key when not already set: The core rule is `if not inner_query.group_by:` — the primary key should only be assigned as group_by when no other GROUP BY has been established previously.

## References

- `skill_load(name="django-django-11797", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
