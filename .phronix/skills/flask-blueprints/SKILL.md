---
name: flask-blueprints
description: The flask-blueprints subject.
subject: flask-blueprints
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Allow dot characters in Blueprint names |


## Instructions

## Rules

### R1 — Allow dot characters in Blueprint names

Do not raise a ValueError when a Blueprint name contains a dot. Blueprint names may include dot characters because tests and nested blueprint support rely on it. Remove the dot‑check or adjust validation logic accordingly.

## References
