# Lessons — django-django-15252

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — ensure_schema creates table on non-default DBs

MigrationRecorder.ensure_schema creates django_migrations table on non-default databases, causing OperationalError. Adding a simple connection.alias != 'default' check after has_table() is insufficient because ensure_schema is called before migrations are run on test databases, leading to missing table error.

## Lessons
