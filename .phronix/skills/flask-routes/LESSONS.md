# Lessons — flask-routes

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Domain column implementation caused test failures

**2026-08-21** — Adding a Domain column to `flask routes` introduced a list comprehension that produced `None` for missing subdomains and did not guard against empty strings. This caused a TypeError when computing column widths and produced entries like `a.None`. It also removed the expected `Subdomain` column, breaking tests expecting it.
