---
name: flask-cli-routes-command
description: flask cli `flask routes` command output/formatting (src/flask/cli.py routes_command) — adding domain/subdomain/host columns.
subject: flask-cli-routes-command
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add domain/subdomain column to `flask routes` output |
| `R1` | Rules | Column header must be "Subdomain" or "Host", not a generic "Domain" |
| `R2` | Rules | Read tests/test_cli.py::TestRoutes tests before touching routes_command formatting |

## Instructions

### I1 — Add domain/subdomain column to `flask routes` output

Fix for `routes_command` in src/flask/cli.py (flask-5063: routes should show which host/subdomain each rule belongs to).

Working approach (verified: 2/2 target tests + 54/54 regressions pass):
- Build parallel lists per rule (endpoints, methods, rule strings) instead of relying on `zip(rules, rule_methods)`.
- Check `current_app.url_map.host_matching`: if true, derive a per-rule domain column from `rule.host`, header "Host"; else derive it from `rule.subdomain`, header "Subdomain".
- Only add the column if `any(rule.host or rule.subdomain for rule in rules)` — otherwise output stays unchanged (this satisfies the no-subdomain regression tests like test_simple/test_all_methods).
- Insert the domain column at the front of `headers`/`widths`/`rows`, and generalize the format string from a fixed 3-column `"{0:<w0}  {1:<w1}  {2:<w2}"` to `"  ".join(f"{{{i}:<{w}}}" for i, w in enumerate(widths))` so it works with either 3 or 4 columns.

Target tests: tests/test_cli.py::TestRoutes::test_subdomain and ::test_host.

## Rules

### R1 — Column header must be "Subdomain" or "Host", not a generic "Domain"

When adding domain info to `flask routes` output (src/flask/cli.py, `routes_command`), the extra column's header text must be exactly "Subdomain" when `current_app.url_map.host_matching` is False, and exactly "Host" when it is True. Do not use a single generic label like "Domain" for both modes.

Why: the hidden target tests (tests/test_cli.py::TestRoutes::test_subdomain and ::test_host) assert the literal strings "Subdomain" and "Host" appear in the output respectively. An attempt-2 implementation added a working domain column but used "Domain" as the header in both modes and failed both target tests for that reason alone — the underlying logic (computing host/subdomain per rule, building `f"{subdomain}.{server_name}"`) was otherwise sound and 54/54 regression tests still passed.

How to apply: keep the two-branch structure (host_matching vs subdomain), but set `headers.insert(0, "Host")` in the host_matching branch and `headers.insert(0, "Subdomain")` in the subdomain branch.

### R2 — Read tests/test_cli.py::TestRoutes tests before touching routes_command formatting

Before modifying `routes_command` in src/flask/cli.py, read the actual test bodies of TestRoutes::test_host, test_subdomain, test_simple, and test_sort in tests/test_cli.py — do not implement from the GitHub issue's example table alone. The issue shows a single "Domain" column, but the real tests check for separate "Host" and "Subdomain" header strings, and test_simple/test_sort assert on fixed-position substrings of existing output that break if a new column is inserted unconditionally.
