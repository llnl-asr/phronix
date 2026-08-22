---
name: flask-cli-routes-domain-column
description: Adding a Domain/Host/Subdomain column and --sort=domain to `flask routes` in src/flask/cli.py, so subdomain- or host-matched routes show which domain they belong to.
subject: flask-cli-routes-domain-column
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add a domain/host/subdomain column to `flask routes` |
| `R1` | Rules | Don't keep attrgetter(sort) once "domain" is a sort choice |



## Instructions

### I1 — Add a domain/host/subdomain column to `flask routes`

Problem: `routes_command` in `src/flask/cli.py` only prints Endpoint/Methods/Rule, with no way to see which subdomain/host a route belongs to. Target tests: `TestRoutes::test_subdomain`, `TestRoutes::test_host` in `tests/test_cli.py`.

Working pipeline (confirmed: 2/2 target tests + 54/54 regressions passed):
1. `host_matching = current_app.url_map.host_matching`.
2. `has_domain = any(rule.host if host_matching else rule.subdomain for rule in rules)` — only add the column when at least one rule has a domain, so apps without subdomains keep the old 3-column output.
3. Build each row as a list: `[endpoint, methods, (host_or_subdomain if has_domain), rule.rule]`.
4. Build `headers`/`sorts` lists in the same conditional order as row columns: `["Endpoint","Methods"]`, then `"Host"`/`"Subdomain"` + `"domain"` only if `has_domain`, then `"Rule"`/`"rule"`.
5. Add `"domain"` to the `--sort` `click.Choice(...)`.
6. Sort via `rows.sort(key=itemgetter(sorts.index(sort)))` in `try/except ValueError` so `--sort=domain` no-ops when there's no domain column.
7. Compute column widths from header+data rows uniformly; format with a generated template, not the old fixed 3-column string.

## Rules

### R1 — Don't keep attrgetter(sort) once "domain" is a sort choice

Do not try to keep the original `sorted(rules, key=attrgetter(sort))` approach when adding "domain" as a sort option. `Rule` objects have no uniform `.domain` attribute — it's `.host` under host-matching, `.subdomain` otherwise, and absent as a real attribute name. Build row-lists first and sort with `itemgetter(index)` against a `sorts` list instead; this sidesteps needing an attribute that doesn't uniformly exist. Evidence: `src/flask/cli.py` `routes_command`, confirmed by `TestRoutes::test_subdomain`/`test_host` passing (2/2 target, 54/54 regressions).

## References
