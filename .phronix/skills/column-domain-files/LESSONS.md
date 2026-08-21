# Lessons — column-domain-files

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — append-subdomain-column-to-routes-table does not work

**Tried**: append-subdomain-column-to-routes-table

**Hypothesis**: Adding a "Subdomain" column at the END of the routes_command table (after Rule, not before Endpoint) satisfies the issue's request while keeping tests/test_cli.py::TestRoutes passing, since expect_order only checks that each line STARTS WITH the endpoint name (line[:len(expect)] == expect) — a trailing column doesn't touch that prefix. Falsified if hidden tests expect the domain as the leading/fir

**Refuted by**: test 0/1, train 0/2. Do not re-propose this without new evidence.

### P2 — append-subdomain-column-to-routes-table does not work

**Tried**: append-subdomain-column-to-routes-table

**Hypothesis**: Adding a "Subdomain" column at the END of the routes_command table (after Rule, not before Endpoint) satisfies the issue's request while keeping tests/test_cli.py::TestRoutes passing, since expect_order only checks that each line STARTS WITH the endpoint name (line[:len(expect)] == expect) — a trailing column doesn't touch that prefix. Falsified if hidden tests expect the domain as the leading/fir

**Refuted by**: test 0/1, train 0/5, validate 0/1. Do not re-propose this without new evidence.

## Lessons
