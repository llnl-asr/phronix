# Lessons — django-django-14999

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Attempting to rename without checking db_table

If the guard is omitted, RenameModel will drop/recreate constraints leading to failures on PostgreSQL.

### P2 — Providing a full asgiref implementation

A full implementation is unnecessary; a stub is sufficient and avoids extra dependencies.

## Lessons
