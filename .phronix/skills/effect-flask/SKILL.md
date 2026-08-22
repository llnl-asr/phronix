---
name: effect-flask
description: Research on effect flask. Covers how does host_matching flag change the presence and order of the Host column in `flask routes` output; what is the impact of SERVER_NAME being set or unset on the Subdomain column ordering; when both host_matching is true and SERVER_NAME is set, how are Domain and Subdomain columns ordered relative to each other. Approaches tried: src/flask/blueprints.py, src/flask/cli.py, src/flask/helpers.py, src/flask/testing.py.
subject: effect-flask
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to effect flask |
| `X1` | References | Where research on this subject stands |



## Instructions

### I1 — How to evaluate a change to effect flask

Figure of merit: **flask_routes_metric** (max, target 1.0).

Measured by: count of correctly ordered domain/subdomain columns in `flask routes` output

Cases differ along: host_matching, server_name, subdomain.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **flask_routes_metric** (max, target 1.0).

**Still open**
- src/flask/blueprints.py, src/flask/cli.py, src/flask/helpers.py, src/flask/testing.py (potential)
- aspect not yet answered: host_matching_effect
- aspect not yet answered: server_name_effect
- aspect not yet answered: combined_effect

**Where the detail is**
- src/flask/blueprints.py, src/flask/cli.py, src/flask/helpers.py, src/flask/testing.py: benchmark attempt
- full record: research topic `pallets__flask-4045` (via research_status, only if this summary is not enough)
