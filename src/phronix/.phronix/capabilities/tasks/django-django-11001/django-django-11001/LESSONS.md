# Lessons — django-django-11001

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — order_by duplicate detection fails with multiline RawSQL

**2026-08-29** — Duplicate detection in SQLCompiler.get_order_by fails for multiline RawSQL queries because the regular expression only sees the last line, causing later order_by clauses to be incorrectly omitted.
Workaround: ensure each RawSQL clause ends with a unique whitespace or comment, or preprocess the SQL to remove newlines before duplicate detection.
