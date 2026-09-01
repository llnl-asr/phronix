# Lessons — django-django-15320

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Do not omit setting subquery flag; failing to set `query

Do not omit setting subquery flag; failing to set `query.subquery = True` leaves the flag false, causing test_subquery_sql to fail and introducing regressions in boolean expression handling.

## Lessons
