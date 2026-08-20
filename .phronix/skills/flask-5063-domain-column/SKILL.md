---
name: flask-5063-domain-column
description: The flask-5063-domain-column subject.
subject: flask-5063-domain-column
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `X1` | References | Task is adding a new Domain column to `flask routes` |


## Instructions

## Rules

## References

### X1 — Task is adding a new Domain column to `flask routes`

flask-5063: this checkout's routes_command (src/flask/cli.py ~line 1001) currently outputs only Endpoint, Methods, Rule — no domain/subdomain column exists yet, and no test in tests/test_cli.py TestRoutes (~lines 415-500) exercises subdomains or SERVER_NAME. The task is to add a Domain column; the exact intended format string (e.g. `<subdomain>.<server_name>` vs raw `rule.subdomain` vs literal fallback text) was NOT determined from this repo/checkout — no upstream PR/commit for issue 5063 was found locally (no network access). That format decision must come from the task brief or a reference patch, not from in-repo evidence. See [[flask-routing-subdomain]] for the underlying subdomain/SERVER_NAME mechanics informing that decision.
