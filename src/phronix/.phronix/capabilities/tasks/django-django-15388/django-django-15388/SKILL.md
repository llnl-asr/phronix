---
name: django-django-15388
description: Diagnosis for django issue django-11797 where filtering on a query result that uses values() + annotate() causes the subsequent filter() call to use the wrong GROUP BY column
subject: django-11797 GROUP BY preservation issue
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Diagnosis for django-11797 GROUP BY preservation |
| `R1` | Rules | Constraint: preserve existing template watch behavior |
| `R2` | Rules | Diagnosis for Django SWE-bench task 15388 |
| `R3` | Rules | Task context and SWE-bench scope |

## Instructions

### I1 — Problem description

Dev server fails to restart after adding BASE_DIR to TEMPLATES[0]['DIRS'] in settings, causing test_non_template_changed_in_template_directory to fail.

### I2 — Key idea

`autoreload.template_changed` incorrectly returns True for non‑template file changes inside a template directory, so the dev server does not restart.

### I3 — Instructions to solve it

1. Open `django/utils/autoreload.py`.
2. Locate the `template_changed` function.
3. Modify its logic to return `None` for files that are inside a template directory but are not actual template files (e.g., non‑`.html` files).
   ```python
   def template_changed(event, path):
       # existing checks …
       if path.is_dir():
           return None
       # New check: ignore files inside a template directory that are not templates
+      if any(path.match('*.html') for dir in settings.TEMPLATES[0]['DIRS'] if path.is_relative_to(dir)):
+          return None
       # original logic …
   ```
4. Add a comment explaining the rationale.
5. Run the target test `test_non_template_changed_in_template_directory` to confirm it now returns `None`.
6. Ensure all regression tests still pass.

### I4 — Diagnosis for django-11797 GROUP BY preservation

Issue: Filtering on a query result that uses values() + annotate() causes the subsequent filter() call to use the wrong GROUP BY column.

Problem pattern:
  a = models.User.objects.filter(email__isnull=True).values('email').annotate(m=Max('id')).values('m')
  b = models.User.objects.filter(id=a[:1])  # Bad: GROUP BY U0."id" should be GROUP BY U0."email"

Root cause: When a[:1] evaluates the queryset (via __getitem__ -> list(qs)), the GROUP BY context from values('email') is lost. When filter(id=a[:1]) creates a new query, it defaults to GROUP BY the primary key (id) instead of preserving the annotated field (email).

Fix attempted in attempt 1: Added `if not inner_query.group_by:` check before setting group_by to primary key. This prevents overwriting but doesn't actively preserve the correct GROUP BY fields.

Why it's incomplete: The check only prevents overwriting an already-set group_by, but the GROUP BY fields from the original values('email') clause are never carried forward through the subquery evaluation. The new query has no knowledge of the original grouping fields.

Test result: test_exact_query_rhs_with_selected_columns still fails, confirming the fix is incomplete.

## Rules

### R1 — Constraint: preserve existing template watch behavior

Do not alter the existing handling of template files; any change must continue to return True for genuine template file modifications so that template reloads still occur.

### R2 — Diagnosis for Django SWE-bench task 15388

Task: Django SWE-bench issue #15388. This is a benchmark task for diagnosing and fixing a Django framework issue.

Key facts:
- Repository at attempt-2 stage, branch main
- Recent commits include SWE-bench refactoring and issue fixes (#33476, #32243)
- Part of the phronix-bench SWE-bench evaluation suite

Diagnosis guideline: Document the problem, relevant code areas, and proposed fix approach for the Django issue without exceeding block limits.

### R3 — Task context and SWE-bench scope

This task is part of the SWE-bench benchmark for Django issue #15388. The working directory contains the Django codebase at a specific commit state. The diagnosis should document:
1. The problem described in issue #15388
2. Relevant code sections that need modification
3. The expected fix approach
4. Any test cases that validate the fix

The SWE-bench task framework evaluates the agent's ability to understand, diagnose, and fix the described issue.

## References

- `skill_load(name="django-django-15388", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
