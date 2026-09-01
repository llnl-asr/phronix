# Lessons — pallets-flask-5063

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — The routes command added a Domain column and renamed it to Host, but t

**2026-08-31** — The routes command added a Domain column and renamed it to Host, but the tests expected a Host column with specific ordering. The implementation output `<default>` in the wrong column, causing header mismatches and ordering failures for `test_simple`, `test_sort`, `test_subdomain`, and `test_host`.
