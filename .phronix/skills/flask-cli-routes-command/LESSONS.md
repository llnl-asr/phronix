# Lessons — flask-cli-routes-command

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Attempt 3: added single "Domain" column, hidden tests expect "Subdomain" and "Host" as separate columns

**2026-08-20** — Task: `flask routes` should expose subdomain/host info per rule (pallets/flask-5063).

Attempt 3 added one combined "Domain" column (built from `rule.subdomain` + `app.config['SERVER_NAME']`, formatted as `f"{subdomain}.{server_name}"`) to `routes_command` in src/flask/cli.py. It failed both hidden target tests:
- tests/test_cli.py::TestRoutes::test_subdomain — asserts `"Subdomain" in result.output`
- tests/test_cli.py::TestRoutes::test_host — asserts `"Host" in result.output`

Root cause: the hidden tests check for the literal column header strings "Subdomain" and "Host" — these are two distinct pieces of information/columns, not one merged "Domain" column. A single "Domain" header will never satisfy either assertion regardless of its cell contents.

Fix direction (not yet verified): add two separate columns/headers named exactly "Subdomain" and "Host" (or add a `--host`/similar flag producing a "Host" header, since test_host and test_subdomain are separate test methods — they may correspond to two different CLI options/output modes rather than two simultaneous columns). Read the actual hidden test bodies if a future attempt can capture full pytest output with `-s`/verbose diffs, since only the assertion lines were visible here (`tests/test_cli.py:495` and `:504`), not the full test source or setup (e.g. what `SERVER_NAME`/subdomain config the test fixture uses).
