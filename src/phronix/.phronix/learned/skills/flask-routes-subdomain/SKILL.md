---
name: flask-routes-subdomain
description: The flask-routes-subdomain subject.
subject: flask-routes-subdomain
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `X1` | References | Actual flask-5063 issue: subdomain info in `flask routes` output |


## Instructions

## Rules

## References

### X1 — Actual flask-5063 issue: subdomain info in `flask routes` output

flask-5063 is a feature request: `flask routes` CLI should show which subdomain each route belongs to (from `app.register_blueprint(..., subdomain=...)` / `SERVER_NAME` config), not just Endpoint/Methods/Rule.

Likely relevant files: src/flask/cli.py (routes command), src/flask/app.py, src/flask/blueprints.py (where subdomain/SERVER_NAME attach to url rules). See [[pallets-flask-5063#R4]] for why the assigned pylint-flavored aspect doesn't apply here.
