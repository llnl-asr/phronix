---
name: django-django-13158
description: Diagnosis for Django QuerySet.none() on combined queries returning all results instead of empty. The issue is that QuerySet.none() on combined queries (union, intersection, difference) does not properly propagate the empty state to all branch queries, causing the combinator to return all results instead of empty when the form is submitted empty with ModelMultipleChoiceField using union().
subject: django-django-13158
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis: QuerySet.none() on combined queries |
| `R1` | Rules | QuerySet.none() on combined queries must propagate to all branches |



## Instructions

### I1 — Diagnosis: QuerySet.none() on combined queries

When QuerySet.none() is called on a combined query (union, intersection, difference), it sets the empty state via set_empty(), but this only affects the parent query's where clause. The branch queries within the combinator are not automatically marked as empty, so when the combinator executes, it returns all results from the branches instead of an empty set.

Root cause: In django/db/models/query.py, the _clone() method (or none() method) calls clone.query.set_empty() but does not propagate this to all branch queries in clone.query.combined_queries. This means the combinator's branch queries still have their original where clauses, causing the combined query to return all matching results.

Problem scenario:
- ModelMultipleChoiceField with union() queryset: Publication.objects.filter(id__lt=2).union(Publication.objects.filter(id__gt=5)), required=False
- When form submitted empty: ModelMultipleChoiceField.clean() returns self.queryset.none()
- With regular queryset: none() correctly returns empty queryset
- With combined query (union): none() does not properly empty all branch queries, so the form submits ALL objects matching ANY branch

Diagnosis filed: django-django-13158

## Rules

### R1 — QuerySet.none() on combined queries must propagate to all branches

Rule: When QuerySet.none() is called on a combined query (union, intersection, difference), the set_empty() call must propagate to ALL branch queries in the combinator's combined_queries list. If any branch query remains non-empty, the combinator will return all results from that branch instead of an empty set.

This rule ensures that the fix in django/db/models/query.py _clone() or none() method includes the 3-line addition after clone.query.set_empty():
    if clone.query.combinator:
        for q in clone.query.combined_queries:
            q.set_empty()

Violation of this rule causes the exact bug described in django-django-13158: ModelMultipleChoiceField with union() queryset, when submitted empty, adds ALL objects instead of none.

## References
