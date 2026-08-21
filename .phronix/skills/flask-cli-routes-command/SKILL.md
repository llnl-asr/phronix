---
name: flask-cli-routes-command
description: The flask-cli-routes-command subject.
subject: flask-cli-routes-command
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Do not merge subdomain+server_name into one "Domain" header |


## Instructions

## Rules

### R1 — Do not merge subdomain+server_name into one "Domain" header

In src/flask/cli.py `routes_command`, do not add a single combined "Domain" column for subdomain routing info. The hidden acceptance tests (test_subdomain, test_host in tests/test_cli.py) each assert a distinct literal header string ("Subdomain", "Host") is present in `flask routes` output — a merged "Domain" header satisfies neither. Use separate column names matching those exact strings, or check whether test_host implies a separate CLI flag/mode rather than an always-present column.

Why: attempt 3 verified this fails — output was `Endpoint  Methods  Domain  Rule`, and both `assert "Subdomain" in result.output` and `assert "Host" in result.output` failed.

## References
