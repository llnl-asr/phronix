# Lessons — django-django-13710

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Incorrect pluralisation and unnecessary stubs

**2026-08-29** — Attempted to fix `test_verbose_name_inline` but used naive string concatenation for pluralisation, resulting in incorrect heading `<h2>Non-verbose childss</h2>`. The test expected `<h2>Non-verbose children</h2>`. Additionally, unnecessary stub modules (`asgiref`, `cgi`) were added, cluttering the repo.
