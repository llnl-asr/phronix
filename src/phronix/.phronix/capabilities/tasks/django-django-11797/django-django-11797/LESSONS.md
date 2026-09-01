# Lessons — django-django-11797

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Subquery GROUP BY misalignment

Filtering on query result overrides GROUP BY of internal query leading to incorrect GROUP BY clause in Django ORM subquery when using .filter(id=subquery). This causes GROUP BY on id instead of the intended field (email).

## Lessons

### L1 — Attempt 2 failed due to ImportError: cannot import name 'pass_environm

**2026-08-31** — Attempt 2 failed due to ImportError: cannot import name 'pass_environment' from 'jinja2' when applying the patch. The attempted fix introduced a subquery but did not address the missing import, causing test collection to abort. No target tests passed.
