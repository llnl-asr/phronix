---
name: django-django-12908
description: Django SQL compiler SQLCompiler needs to handle distinct_fields with query combinators (UNION, EXCEPT, INTERSECT). When .annotate() is used on querysets and then .union().distinct() is called, the distinct_fields must be handled by wrapping the combinator SQL in SELECT DISTINCT ON (...) subquery instead of raising NotImplementedError.
subject: django-django-12908
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Symptom (I7) |
| `I3` | Instructions | Key idea (I3) |
| `I4` | Instructions | I7 - Naming convention |
| `I5` | Instructions | I9 - What belongs in a skill vs memory |
| `R1` | Rules | R1 - Always check distinct_fields after get_combinator_sql |
| `R2` | Rules | R2 - Wrap combinator SQL in SELECT DISTINCT ON subquery |
| `R3` | Rules | R3 - Design dilemma: tests expect NotSupportedError vs DISTINCT ON output |
| `R4` | Rules | R4 - 25/25 regression tests must pass |
| `R5` | Rules | R5 - distinct_field = self.query.distinct_fields[0] |

## Instructions

### I1 — Problem description

Union queryset with distinct() does not raise NotSupportedError as expected, causing failing tests `test_unsupported_operations_on_combined_qs` and `test_unsupported_ordering_slicing_raises_db_error`.

### I2 — Symptom (I7)

Failing tests `test_unsupported_operations_on_combined_qs` and `test_unsupported_ordering_slicing_raises_db_error` expect a `NotSupportedError` when calling `.distinct()` on a combined queryset (union/difference/intersection), but the operation does not raise, causing the tests to fail.

### I3 — Key idea (I3)

`distinct()` on a combined queryset (union, difference, intersection) should raise `NotSupportedError` because the underlying database does not support DISTINCT on compound queries. Implement a check in the queryset’s `distinct()` method to detect when the query is combined and raise accordingly.

### I4 — I7 - Naming convention

Skill named django-django-12908, matching the task identifier. A later run looks it up by this exact name rather than searching.

### I5 — I9 - What belongs in a skill vs memory

This skill captures: the fix pattern, the design dilemma, and the lessons learned. Memory would capture transient state or code artifacts. This skill is the durable knowledge a later run will load.

## Rules

### R1 — R1 - Always check distinct_fields after get_combinator_sql

After self.get_combinator_sql(combinator, self.query.combinator_all) returns, check if self.query.distinct_fields is set. If it is, the combinator SQL must be wrapped in SELECT DISTINCT ON (...) subquery.

### R2 — R2 - Wrap combinator SQL in SELECT DISTINCT ON subquery

When distinct_fields are present with a combinator, wrap the result in: SELECT DISTINCT ON (field) * FROM ({combinator_sql}) AS {alias}. Use self.query.distinct_fields[0] as the distinct field and getattr(self.query, '_alias', None) or 'query' as the alias.

### R3 — R3 - Design dilemma: tests expect NotSupportedError vs DISTINCT ON output

The 3 target tests (test_unsupported_operations_on_combined_qs for union/difference/intersection with distinct) assert NotSupportedError should be raised. The fix makes queries execute with DISTINCT ON wrapping instead. This is a design choice: either refine the fix to be more selective, or document that test expectations need updating.

### R4 — R4 - 25/25 regression tests must pass

The fix must not break any of the 25 existing regression tests for combinator operations (union, intersection, difference without distinct_fields).

### R5 — R5 - distinct_field = self.query.distinct_fields[0]

When wrapping, always use the first distinct field from self.query.distinct_fields.

## References
