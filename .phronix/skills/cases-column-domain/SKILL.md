---
name: cases-column-domain
description: Research on cases column domain. Covers what subdomain information is available in Werkzeug Rule objects; how should subdomain and SERVER_NAME be combined for display; how to extend the routes command output table structure. Approaches tried: add domain column full, add subdomain column only, add domain column smart fallback, subdomain servername concatenation.
subject: cases-column-domain
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to cases column domain |
| `X1` | References | Tried: add-domain-column-full |
| `X2` | References | Tried: add-subdomain-column-only |
| `X3` | References | Tried: add-domain-column-smart-fallback |
| `X4` | References | Tried: subdomain-servername-concatenation |
| `X5` | References | Tried: dynamic-format-list-based |
| `X6` | References | Tried: fallback-chain-edge-cases |
| `X7` | References | Tried: conditional-domain-column |
| `X8` | References | Tried: sort-by-domain-rule-level |
| `X9` | References | Tried: sort-by-domain-row-level |
| `X10` | References | Sources consulted for cases column domain |












## Instructions

### I1 — How to evaluate a change to cases column domain

Figure of merit: **subdomain_column_present** (max, target 1.0).

Measured by: Binary check: run `flask routes` command programmatically and verify that (1) output contains a "Domain" or "Subdomain" column header, (2) subdomain values are correctly shown for routes registered with subdomain parameter, (3) the full domain (subdomain.SERVER_NAME or just SERVER_NAME) is displayed in the new column. Score 1.0 if all three conditions met, 0.0 otherwise.

Cases differ along: route_type, server_name_set, subdomain_type.

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

### X4 — Tried: subdomain-servername-concatenation

Combine rule.subdomain with SERVER_NAME config using pattern: subdomain.SERVER_NAME when both present, with fallbacks to either value alone or '-' when missing. Preserves ports and nested subdomains.

**Hypothesis**: The combination pattern subdomain.SERVER_NAME matches Flask's actual routing behavior and will correctly display full domain information for routes with subdomains.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: dynamic-format-list-based

Refactor routes_command to use list-based row building with dynamic format string generation, enabling variable column count. Changes: headers tuple→list, collect rows as lists, calculate widths dynamically, build format string with join. Handles conditional domain column cleanly.

**Hypothesis**: Converting from hardcoded 3-column format to dynamic list-based row building allows adding a 4th domain column conditionally without breaking existing output. The format string pattern can be generated dynamically using join of format parts.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: fallback-chain-edge-cases

Implement 4-level fallback: (1) subdomain + SERVER_NAME → 'subdomain.SERVER_NAME', (2) subdomain only → 'subdomain', (3) SERVER_NAME only → 'SERVER_NAME', (4) neither → '-'. Handles nested subdomains, ports, wildcards, and None/empty values.

**Hypothesis**: A fallback chain (both→subdomain-only→servername-only→placeholder) handles all edge cases including missing values, empty strings, and dynamic patterns without errors.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: conditional-domain-column

Domain column displayed only when at least one route has domain info (subdomain or host). Prevents breaking existing apps without domain routing. No user flag needed - automatic detection based on route content.

**Hypothesis**: Using conditional display (has_domain check) instead of always showing domain column maintains backward compatibility. Column only appears when any(rule.host or rule.subdomain), keeping output clean for apps without domain routing.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: sort-by-domain-rule-level

Add "domain" to sort choices (line 992). Sort rules before row building using lambda accessing rule.host or rule.subdomain based on host_matching flag. Empty/None domains sort first via 'or ""' fallback. Maintains consistency with existing endpoint/methods/rule sorting approach.

**Hypothesis**: Adding "domain" to sort choices and sorting rules by (rule.host if host_matching else rule.subdomain) before building rows maintains the current sorting architecture while enabling domain sorting. None values handled with 'or ""' to sort empty domains first.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Tried: sort-by-domain-row-level

REFUTED: Sorting rows after building with itemgetter. Reason: More invasive than sorting rules before building. Current code sorts rules before processing; maintaining that pattern is cleaner. Would require new import and restructuring all sorting logic. The simpler approach of sorting rules with la

**Hypothesis**: Sorting rows (lists) after building using itemgetter would enable domain sorting but requires refactoring the entire sorting flow and importing itemgetter.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X10 — Sources consulted for cases column domain

- Analysis comparing rule-level vs row-level sorting. Considered upstream PR pattern but found rule-level sorting simpler for this codebase.
- Analysis of current cli.py implementation and testing of has_domain detection logic. Pattern matches upstream PR design philosophy.
- Combined edge case analysis with issue requirements
- Flask 2.3 config docs (https://flask.palletsprojects.com/en/2.3.x/config/), tests/test_basic.py lines 1436-1478 (test_server_name_subdomain), src/flask/blueprints.py lines 380-390 (nested subdomain co
- Issue example line 36-41, Flask SERVER_NAME documentation, current routes_command implementation
- src/flask/blueprints.py lines 380-390, tests/test_basic.py subdomain tests, Flask 2.3 config docs
