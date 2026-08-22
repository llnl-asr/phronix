---
name: flask-routes-domain-fix
description: The flask-routes-domain-fix subject.
subject: flask-routes-domain-fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add domain column to routes command |
| `I2` | Instructions | Implement domain column in routes command |
| `I3` | Instructions | Modify src/flask/cli.py for domain column |
| `I4` | Instructions | Compute domain info for routes |
| `I5` | Instructions | Placeholder |
| `I6` | Instructions | Edit src/flask/cli.py |
| `I7` | Instructions | Modify src/flask/cli.py |
| `R1` | Rules | Do not adjust PYTHONPATH to affect Flask routes output |
| `R2` | Rules | The default `flask routes` command does not show subdomain information |










## Instructions

### I1 — Add domain column to routes command

Modify src/flask/cli.py to compute server_name, rule_domains, and include Domain column in output.

### I2 — Implement domain column in routes command

Modify src/flask/cli.py to compute server_name, rule_domains, and include Domain column in the routes command output. This adds a Domain column showing subdomain or host for each rule, based on rule.subdomain and the SERVER_NAME config.

### I3 — Modify src/flask/cli.py for domain column

Edit src/flask/cli.py: In routes_command, after retrieving rules, compute server_name = current_app.config.get('SERVER_NAME', '') and rule_domains = [ (f"{rule.subdomain}.{server_name}" if rule.subdomain else server_name) for rule in rules ]. Then update headers to include "Domain" and compute widths accordingly, adding a column for domain. Update the row format string to include the domain column and output it in the loop: click.echo(row.format(rule.endpoint, methods, domain, rule.rule).rstrip()).

### I4 — Compute domain info for routes

In routes_command, compute server_name = current_app.config.get('SERVER_NAME', '') and rule_domains = [f"{rule.subdomain}.{server_name}" if getattr(rule, 'subdomain', None) else server_name for rule in rules].

### I5 — Placeholder

Placeholder

### I6 — Edit src/flask/cli.py

TODO

### I7 — Modify src/flask/cli.py

TODO

## Rules

### R1 — Do not adjust PYTHONPATH to affect Flask routes output

Changing the import path via `sitecustomize.py` does not add the missing Host and Subdomain columns to the `flask routes` CLI output. The missing information is due to the CLI implementation, not module import locations. Future fixes should modify `src/flask/cli.py` to compute and display the domain information.

### R2 — The default `flask routes` command does not show subdomain information

The standard Flask CLI `flask routes` only lists the endpoint, methods, and rule; it does not include subdomain or host information. Adjusting PYTHONPATH or environment does not affect this. To include subdomain data, modify `src/flask/cli.py` to compute a Domain column based on each rule's `subdomain` attribute and the app's `SERVER_NAME` configuration, as described in the instructions of this skill.

## References
