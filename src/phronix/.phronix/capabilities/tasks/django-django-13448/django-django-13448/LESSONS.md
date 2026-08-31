# Lessons — django-django-13448

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Failed fix expectation for migrate flag false

**2026-08-29** — I7

### L2 — Pitfalls and lessons

**2026-08-29** — - Adding only a `cgi.py` stub resolves import errors but does **not** prevent the `migrate` command from being called; the test still fails because it expects `migrate` not to be invoked when `TEST['MIGRATE']=False`.
- Attempting to mock `migrate` without proper scoping can break other tests or production behavior; ensure any mock is limited to the test runner environment.
- Over‑engineering the stub (e.g., implementing full CGI functionality) is unnecessary and adds maintenance burden.
- Changing database settings globally can affect other test cases; apply the `TEST['MIGRATE']=False` only in the specific test configuration.
