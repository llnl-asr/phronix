---
name: pallets-flask-5063
description: The pallets-flask-5063 subject.
subject: pallets-flask-5063
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | werkzeug Rule.subdomain attribute not directly confirmed |
| `R2` | Rules | No existing precedent for --sort domain or CHANGES.rst mention |
| `X1` | References | routes_command existing formatting pattern (src/flask/cli.py ~988-1034) |




## Instructions

## Rules

### R1 — werkzeug Rule.subdomain attribute not directly confirmed

The investigation inferred that werkzeug's `Rule` object exposes a `.subdomain` attribute (populated via Flask's Blueprint `subdomain=` kwarg) but did NOT verify this by reading werkzeug source directly — only Flask's own docstring at src/flask/app.py:995 was checked. Before implementing the Domain column value, confirm `Rule.subdomain` exists and its unset-value semantics (empty string vs None) by checking werkzeug.routing.Rule source. Do not assume truthiness handling without this check.

### R2 — No existing precedent for --sort domain or CHANGES.rst mention

Grepped CHANGES.rst for "domain"/"routes" — no mention of a Domain column or related feature; this is confirmed unreleased/pending with no maintainer release-note wording to mirror. Grepped cli.py for "--sort", "--all-methods", "def routes" — confirmed the only existing --sort choices are ("endpoint", "methods", "rule", "match"); there is no "domain" sort choice today and no other precedent that adding a column forces a matching sort choice. Treat "add --sort domain" as speculative, not required by the issue.

## References

### X1 — routes_command existing formatting pattern (src/flask/cli.py ~988-1034)

The `flask routes` command builds headers as a plain tuple `("Endpoint", "Methods", "Rule")`, computes each column width as `max(len(header), max(len(value) for rows))`, and builds a dynamic row format string `"{{0:<{0}}}  {{1:<{1}}}  {{2:<{2}}}".format(*widths)` — left-justified columns, two-space gutter, dashes for the separator row sized to column widths. Header row is `.strip()`ed; each data row is `.rstrip()`ed. Any new column (e.g. "Domain") should extend this same pattern rather than introducing a different layout mechanism.
