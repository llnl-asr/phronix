---
name: flask-cli-domain-column-fix
description: Added domain column to flask CLI routes command
metadata:
  type: project
---

Implemented domain column logic in src/flask/cli.py to show subdomain/host information in `flask routes` output, matching Flask behavior.
**Why:** Issue required domain display for subdomains.
**How to apply:** The `routes_command` now computes per-rule domain values and conditionally adds a 'Domain' column.
