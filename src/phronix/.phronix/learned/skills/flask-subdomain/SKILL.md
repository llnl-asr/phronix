---
name: flask-subdomain
description: Research on flask subdomain. Covers how does Flask associate routes with subdomains internally; does the app's url_map contain subdomain information for each rule; what data is stored when registering a blueprint with a subdomain. Approaches tried: sitecustomize.py, src/flask/cli.py, src/flask/globals.py.
subject: flask-subdomain
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to flask subdomain |
| `X1` | References | Where research on this subject stands |




## Instructions

### I1 — How to evaluate a change to flask subdomain

Figure of merit: **failing-tests** (min, target 0.0).

Measured by: count of failing target tests after applying fix

Cases differ along: app_context, subdomain_handling.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **failing-tests** (min, target 0.0).

**Still open**
- sitecustomize.py, src/flask/cli.py, src/flask/globals.py (potential)
- aspect not yet answered: subdomain_routing_inspection
- aspect not yet answered: url_map_subdomain_keys
- aspect not yet answered: blueprint_subdomain_registration
- aspect not yet answered: flask_routes_cli_extension
- aspect not yet answered: subdomain_info_in_routes

**Where the detail is**
- sitecustomize.py, src/flask/cli.py, src/flask/globals.py: benchmark attempt
- full record: research topic `pallets__flask-5063` (via research_status, only if this summary is not enough)