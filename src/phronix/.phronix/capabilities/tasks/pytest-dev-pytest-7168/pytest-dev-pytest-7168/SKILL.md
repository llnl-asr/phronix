---
name: pytest-dev-pytest-7168
description: The pytest-dev-pytest-7168 subject.
subject: pytest-dev-pytest-7168
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem it solves |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Diagnosis for pytest-dev-pytest-7168 - saferepr exception handling |
| `R1` | Rules | Constraints |

## Instructions

### I1 — Problem it solves

Detects and fixes failing pytest tests caused by an INTERNALERROR when an object's __repr__ raises during attribute access, specifically the test_subquery_sql failure in Django's query generation. This skill applies when a test crashes with an INTERNALERROR stack trace rooted in __repr__ issues.

### I2 — Key idea

The fix requires preventing slicing of the generated subquery SQL and providing stub modules for missing asgiref imports, ensuring Subquery.as_sql returns the full SQL string without truncation.

### I3 — Instructions to solve it

1. Open `django/db/models/sql/subqueries.py` (or the relevant `expressions.py` file containing `Subquery.as_sql`).
2. Replace the line that slices the SQL string (e.g., `subquery_sql = sql[:10]`) with `subquery_sql = sql` to use the full generated SQL.
3. Add minimal stub modules for `asgiref` to unblock imports:
```
# Create file asgiref/__init__.py
class SyncToAsync:
    def __init__(self, func):
        self.func = func
    async def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)
```
4. Ensure any `functools.lru_cache` decorators are applied correctly (no missing arguments).
5. Run the test suite; the previously failing `test_subquery_sql` should now pass.

### I4 — Diagnosis for pytest-dev-pytest-7168 - saferepr exception handling

Problem: _format_repr_exception in saferepr.py fails when __getattribute__ raises and repr() is called. Exception's __repr__ may itself fail. Nested exception contexts create chain failures. Current try/except only catches one level.

Root cause: _format_repr_exception calls _try_repr_or_str(exc) which calls repr(exc). If repr fails, it falls back to type name. But when called from SafeRepr.repr() during its own exception handling, the outer call may fail before inner protection applies. test_broken_getattribute demonstrates this.

Fix needed: _format_repr_exception must have a top-level fallback catching ALL exceptions from the formatting chain, returning just the exception type name.

Why this matters: Without fix, classes with broken __getattribute__ or __repr__ cause crashes/RecursionError in pytest error reporting.

## Rules

### R1 — Constraints

Do not modify other parts of `Subquery.as_sql` beyond removing the slicing. Preserve existing functionality and ensure no other tests regress. The stub for asgiref must only provide the minimal API used by Django and should not interfere with real asgiref installations.

## References
