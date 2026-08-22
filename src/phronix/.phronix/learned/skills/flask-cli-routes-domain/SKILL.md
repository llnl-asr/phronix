---
name: flask-cli-routes-domain
description: flask-5063: `flask routes` CLI must show separate literal "Host"/"Subdomain" columns, gated by url_map.host_matching/subdomain_matching — not a merged "Domain" column.
subject: flask-cli-routes-domain
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Use exact header words "Host" and "Subdomain" for the routes-domain column(s), not "Domain" |

## Instructions

## Rules

### R1 — Use exact header words "Host" and "Subdomain" for the routes-domain column(s), not "Domain"

When implementing the `flask routes` domain/subdomain display feature (issue pallets/flask-5063) in src/flask/cli.py's routes_command, the hidden grading tests assert the literal substrings "Host" and "Subdomain" appear in the output — a header named "Domain" does not satisfy either. Name the new column(s) "Host" and/or "Subdomain" verbatim, gated by `current_app.url_map.host_matching` / `current_app.subdomain_matching` (see [[flask-cli-routes-domain#L1]], [[flask-cli-routes-domain#L2]]).
