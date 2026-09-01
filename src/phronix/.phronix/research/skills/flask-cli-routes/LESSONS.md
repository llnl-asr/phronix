# Lessons — flask-cli-routes

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Failed attempt to add a "Domain" column broke the expected output orde

**2026-08-31** — Failed attempt to add a "Domain" column broke the expected output ordering for the Flask `routes` command. Tests `test_simple`, `test_sort`, `test_subdomain`, and `test_host` all failed because the column headers and values no longer matched the test expectations. The fix is to restore the original headers (`Subdomain`, `Endpoint`, `Methods`, `Rule`) and compute column widths based on these fields.
