# Lessons — pallets-flask-5063

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Missing Host column in routes output

**2026-08-31** — Attempt 3 still fails `test_host` and `test_subdomain` because the CLI `routes` command output lacks the Host column. The previous fix added the Subdomain column but omitted Host column and width calculations, resulting in missing columns and failing tests.
