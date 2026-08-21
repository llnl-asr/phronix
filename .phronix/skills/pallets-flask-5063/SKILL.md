---
name: pallets-flask-5063
description: The pallets-flask-5063 subject.
subject: pallets-flask-5063
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add routes subdomain column |


## Instructions

### I1 — Add routes subdomain column

Create a new Flask CLI command `routes-subdomain` that lists routes with a 'Domain' column showing each rule's subdomain.

Implementation steps:
1. Define a click command `routes_subdomain` similar to existing `routes` command.
2. Use `current_app.url_map.iter_rules()` to retrieve each rule.
3. For each rule, get `rule.subdomain` attribute (empty string if none).
4. Format output with columns: Domain, Endpoint, Methods, Rule.
5. Register the command with the FlaskGroup by adding `cli.add_command(routes_subdomain, name="routes-subdomain")`.
6. Ensure the command is deterministic: no model decisions, only deterministic processing.

Add this script to the skill's `skill.py` file under the `pallets__flask-5063` subject.

## Rules

## References
