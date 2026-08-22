---
name: flask-cli-routes
description: The flask-cli-routes subject.
subject: flask-cli-routes
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Include Subdomain column in `flask routes` output |


## Instructions

### I1 — Include Subdomain column in `flask routes` output

When extending the `flask routes` command to display domain information, add a **Subdomain** column (not Domain) that shows the subdomain part of each rule. Compute it using `SERVER_NAME` and the rule's `subdomain` attribute, falling back to an empty string when not set. Update the table header and column widths accordingly, and ensure the column is included in the printed rows.

## Rules

## References
