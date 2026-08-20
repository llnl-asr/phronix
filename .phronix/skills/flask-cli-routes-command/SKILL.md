---
name: flask-cli-routes-command
description: The flask-cli-routes-command subject.
subject: flask-cli-routes-command
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Adding a column to `flask routes` output (src/flask/cli.py routes_command) |


## Instructions

### I1 — Adding a column to `flask routes` output (src/flask/cli.py routes_command)

To add domain/subdomain info to `flask routes`: build `rows` as a list of lists (not parallel arrays), where each row is `[endpoint, methods, (optional domain), rule]`. Only include the domain column when `any(rule.host if host_matching else rule.subdomain for rule in rules)` — host_matching comes from `current_app.url_map.host_matching`, and the column label is "Host" vs "Subdomain" accordingly. Add "domain" to the `--sort` Click.Choice options and sort `rows` with `itemgetter(sorts.index(sort))` where `sorts` is built in parallel with `headers`. Verified working: this exact approach (attempt-1 of pallets__flask-5063) passed all 57 tests in tests/test_cli.py including TestRoutes::test_subdomain and test_host, with zero regressions.

## Rules

## References
