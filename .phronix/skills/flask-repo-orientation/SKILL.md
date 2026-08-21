---
name: flask-repo-orientation
description: Orientation facts about this Flask codebase's structure — where key CLI commands and routing internals live.
subject: flask-repo-orientation
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `X1` | References | `flask routes` CLI command location and its columns |
| `X2` | References | Why this location matters: the flask-5063 issue |



## Instructions

## Rules

## References

### X1 — `flask routes` CLI command location and its columns

The `flask routes` CLI command is `routes_command` in `src/flask/cli.py:988-1034`. It builds its table from `Endpoint`, `Methods`, `Rule` by iterating `current_app.url_map.iter_rules()` — there is no domain/subdomain column.

Werkzeug `Rule` objects do carry domain info even though the table omits it: `.subdomain` (or `.host` when `host_matching` is enabled), which combines with the app's `SERVER_NAME` config to form the full domain. Relevant when a task needs to add a domain/subdomain column to `routes_command` or otherwise surface routing host info.

### X2 — Why this location matters: the flask-5063 issue

The routes_command location and Rule.subdomain fact above (see X1) is the implementation target for pallets__flask-5063, a feature request to show each route's subdomain in `flask routes` output. See [[flask-routes-subdomain#X1]] for the issue itself and [[pallets-flask-5063#R3]] for the output-format constraint that governs how the new column must be added.
