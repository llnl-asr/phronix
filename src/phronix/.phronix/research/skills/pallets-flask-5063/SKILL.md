---
name: pallets-flask-5063
description: What is known about pallets-flask-5063: Add Host column to routes command output, Key idea, Instruction 1: Update email handling in model
subject: pallets-flask-5063
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add Host column to routes command output |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instruction 1: Update email handling in model |
| `I4` | Instructions | Add dot validation to Blueprint and conditional domain column to Flask routes |
| `I5` | Instructions | Attempt to add domain/subdomain info to flask routes |
| `I6` | Instructions | Add optional Host/Subdomain column to flask routes command |


## Instructions

### I1 — Add Host column to routes command output

Modify the `routes_command` in `src/flask/cli.py` to include a new `Host` column in the output. Update the headers, calculate column widths for the Host column, and format each row to display the host information (default empty string if not set). This ensures the CLI `flask routes` command now shows the Host column as required by the tests.

### I2 — Key idea

The email field may be named differently; use a utility to retrieve the correct attribute name and guard against missing values.

### I3 — Instruction 1: Update email handling in model

In the user model, replace direct `user.email` access with `getattr(user, get_email_field_name(), '')` using a utility `get_email_field_name()` that returns the correct attribute name.

### I4 — Add dot validation to Blueprint and conditional domain column to Flask routes

The fix implements two upstream Flask issues:

1. **Blueprint name validation** – `Blueprint.__init__` now raises `ValueError` if the provided `name` contains a dot (`.`). This matches Flask #4045 and prevents ambiguous nested blueprint names.
2. **Domain column in `flask routes`** – The `routes_command` now detects whether the app uses host matching. It builds a list of rule domains, determines if any routes have a domain, and dynamically adds a "Host" or "Subdomain" column with appropriate widths. The table formatting is updated to include the new column only when needed.

Both changes are guarded by idempotent checks and pass all existing tests, including the new target tests for domain information.

**Why**: Provides clearer route output and enforces proper blueprint naming.
**How to apply**: The patches are already merged into `src/flask/blueprints.py` and `src/flask/cli.py`.

### I5 — Attempt to add domain/subdomain info to flask routes

Attempted to modify CLI output but produced no diff; harness error indicates no patch generated.

### I6 — Add optional Host/Subdomain column to flask routes command

Modify src/flask/cli.py: add headers tuple with Host/Subdomain, compute widths, compute domain values per rule, include optional column only when any domain present, build dynamic row format, print rows with domain when applicable.

## Rules
