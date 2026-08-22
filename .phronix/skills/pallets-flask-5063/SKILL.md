---
name: pallets-flask-5063
description: Research on pallets flask 5063. Covers how can flask routes command show domain/subdomain column; why does format string error appear in subdomain test. Approaches tried: src/flask/cli.py.
subject: pallets-flask-5063
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to pallets flask 5063 |
| `I2` | Instructions | Add Domain column to Flask routes command |
| `X1` | References | Where research on this subject stands |






## Instructions

### I1 — How to evaluate a change to pallets flask 5063

Figure of merit: **target-tests-passed** (max, target 2.0).

Measured by: count of target tests passing

Cases differ along: method, server_name, subdomain.

### I2 — Add Domain column to Flask routes command

Update the header tuple to include "Domain" as the first column, adjust column width calculation to account for the new column, compute the domain for each rule safely handling missing SERVER_NAME or subdomain by defaulting to an empty string, and modify the row format string to have four placeholders for Domain, Endpoint, Methods, and Rule. This resolves the missing Domain column and prevents TypeError/ValueError when SERVER_NAME is None.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **target-tests-passed** (max, target 2.0).

**Still open**
- src/flask/cli.py (potential)
- aspect not yet answered: domain-column-output
- aspect not yet answered: error-format-string
- aspect not yet answered: handle-none‑type‑routes
- aspect not yet answered: include‑all‑methods
- aspect not yet answered: optional‑domain‑flag

**Where the detail is**
- src/flask/cli.py: benchmark attempt
- full record: research topic `pallets__flask-5063` (via research_status, only if this summary is not enough)