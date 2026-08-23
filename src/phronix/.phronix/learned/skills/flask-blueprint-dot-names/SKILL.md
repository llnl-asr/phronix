---
name: flask-blueprint-dot-names
description: The flask-blueprint-dot-names subject.
subject: flask-blueprint-dot-names
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `X1` | References | Canonical fix and remaining sibling sprawl: see pallets-flask-4045 |
| `X2` | References | Corrected sibling list — most named siblings don't exist as skills |



## Instructions

## Rules

## References

### X1 — Canonical fix and remaining sibling sprawl: see pallets-flask-4045

The actual task this all serves is pallets-flask-4045 — that skill's R1 states the confirmed complete fix (convert blueprint-name/endpoint/view_func dot checks to `raise ValueError`, all three, not just `Blueprint.__init__`).

Unmerged siblings still duplicating this subject, not yet folded in: flask-blueprint-name-validation, flask-blueprint-dot-validation-complete, flask-blueprint-dotted-names, flask-blueprint-names, flask-blueprint-validation-edit, flask-blueprints, flask-blueprint-dots, flask, blueprint-name, edit-blueprint-file. Next reconcile pass should fold these into pallets-flask-4045 per phronix-learning-reconcile#I1b rather than adding more here.

### X2 — Corrected sibling list — most named siblings don't exist as skills

The sibling list in X1 was written from names seen in research notes, not verified against the store. Checked 2026-08-22 via skill_list: only two of the ten actually exist as skill directories — flask-blueprint-name-validation and flask-blueprint-dot-validation-complete (both orphaned: present on disk under .phronix/learned/skills/ but absent from skill_list's registered index, so skill_write cannot target them by name the normal way). The rest (flask-blueprint-dotted-names, flask-blueprint-names, flask-blueprint-validation-edit, flask-blueprints, flask-blueprint-dots, flask, edit-blueprint-file) do not exist — do not spend a future reconcile pass searching for them. `blueprint-name` exists but is a distinct research-log skill (I1/X1, aspect-based), not a duplicate needing folding. flask-blueprint-name-validation's stale L2 lesson (assert endpoint checks are correct) is now corrected by a superseding lesson on that skill itself, pointing to pallets-flask-4045#R1.
