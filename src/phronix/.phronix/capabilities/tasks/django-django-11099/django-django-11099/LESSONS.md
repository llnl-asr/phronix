# Lessons — django-django-11099

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Unnecessary stub cgi

Adding a stub `cgi.py` works for the test suite but may mask real import issues in production. Ensure the real `cgi` module is available or avoid relying on the stub in deployed environments.

## Lessons
