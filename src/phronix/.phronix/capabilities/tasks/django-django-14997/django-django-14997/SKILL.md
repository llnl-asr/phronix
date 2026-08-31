---
name: django-django-14997
description: The django-django-14997 subject.
subject: django-django-14997
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I7 – Await async connection close |
| `I2` | Instructions | Problem description |



## Instructions

### I1 — I7 – Await async connection close

In `django/db/backends/base/base.py`, locate the cleanup of async connections where `close()` is called without awaiting. Change the call to `await connection.close()` and wrap it in a `try/except RuntimeError` block to handle potential errors during cleanup. This ensures proper resource release and prevents intermittent test failures. After the change, run the async database tests to verify that the issue is resolved.

### I2 — Problem description

Migration fails on SQLite due to a unique constraint that uses a dot operator in the index expression.

## Rules

## References

- `skill_load(name="django-django-14997", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

