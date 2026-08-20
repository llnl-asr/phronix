---
name: column-domain
description: Research on column domain. Covers what subdomain information is available in Werkzeug Rule objects; how should subdomain and SERVER_NAME be combined for display; how to extend the routes command output table structure. Approaches tried: add domain column full, add subdomain column only, add domain column smart fallback.
subject: column-domain
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to column domain |
| `I2` | Instructions | How to solve column domain |
| `X1` | References | Tried: add-domain-column-full |
| `X2` | References | Tried: add-subdomain-column-only |
| `X3` | References | Tried: add-domain-column-smart-fallback |
| `X4` | References | Sources consulted for column domain |
| `X5` | References | What has been investigated about column domain |








## Instructions

### I1 — How to evaluate a change to column domain

Figure of merit: **subdomain_column_present** (max, target 1.0).

Measured by: Binary check: run `flask routes` command programmatically and verify that (1) output contains a "Domain" or "Subdomain" column header, (2) subdomain values are correctly shown for routes registered with subdomain parameter, (3) the full domain (subdomain.SERVER_NAME or just SERVER_NAME) is displayed in the new column. Score 1.0 if all three conditions met, 0.0 otherwise.

Cases differ along: route_type, server_name_set, subdomain_type.

### I2 — How to solve column domain

Try these in order. Ranked by measured **subdomain_column_present** (max, target 1.0). Each one's hypothesis and evidence is in the matching `Tried:` reference on this skill.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. **add-domain-column-full** — subdomain_column_present 1.000, potential — Add a "Domain" column showing full domain (subdomain.SERVER_NAME) for each route
2. **add-subdomain-column-only** — subdomain_column_present 0.600, potential — Add a "Subdomain" column showing only the subdomain value without SERVER_NAME
3. **add-domain-column-smart-fallback** — subdomain_column_present unmeasured, potential — Add Domain column with conditional logic handling all SERVER_NAME/subdomain combinations

## Rules

## References

### X1 — Tried: add-domain-column-full

Add a "Domain" column showing full domain (subdomain.SERVER_NAME) for each route

**Hypothesis**: Adding a Domain column that combines rule.subdomain with current_app.config['SERVER_NAME'] will display full domain info as requested in issue. Falsified if: (1) rule.subdomain is not accessible, (2) SERVER_NAME combination logic doesn't match Flask's URL generation, or (3) output format breaks existing parsing tools.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: add-subdomain-column-only

Add a "Subdomain" column showing only the subdomain value without SERVER_NAME

**Hypothesis**: Adding a "Subdomain" column showing only rule.subdomain value (without SERVER_NAME) is simpler and handles missing SERVER_NAME gracefully. Falsified if: users need full domain reconstruction, or column is confusing without context.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: add-domain-column-smart-fallback

Add Domain column with conditional logic handling all SERVER_NAME/subdomain combinations

**Hypothesis**: Add Domain column with smart fallback: show full domain (subdomain.SERVER_NAME) when both exist, show subdomain alone if no SERVER_NAME, show SERVER_NAME alone if no subdomain, show '-' if neither. Falsified if: logic becomes too complex, edge cases still fail, or users prefer simpler display.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Sources consulted for column domain

- Combined edge case analysis with issue requirements
- Issue example line 36-41, Flask SERVER_NAME documentation, current routes_command implementation

### X5 — What has been investigated about column domain

Ground already covered by research on this subject.

- **werkzeug-rule-api** — What subdomain information is available in Werkzeug Rule objects?
  Looked in: Werkzeug documentation, Rule class implementation, and rule.subdomain attribute behavior
- **server-name-combination** — How should subdomain and SERVER_NAME be combined for display?
  Looked in: Flask configuration docs, SERVER_NAME semantics, subdomain matching behavior in Flask/Werkzeug
- **cli-output-formatting** — How to extend the routes command output table structure?
  Looked in: Current routes_command implementation in cli.py, click output formatting, column width calculation
- **edge-cases** — How to handle edge cases: no SERVER_NAME, empty subdomain, wildcard subdomains?
  Looked in: Flask subdomain matching documentation, test cases in test_blueprints.py, edge case behavior
