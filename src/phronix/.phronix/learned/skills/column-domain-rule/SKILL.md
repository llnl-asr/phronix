---
name: column-domain-rule
description: Research on column domain rule. Covers what subdomain information is available in Werkzeug Rule objects; how should subdomain and SERVER_NAME be combined for display; how to extend the routes command output table structure. Approaches tried: add domain column full, add subdomain column only, add domain column smart fallback, subdomain servername concatenation.
subject: column-domain-rule
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to column domain rule |
| `X1` | References | Tried: add-domain-column-full |
| `X2` | References | Tried: add-domain-column-smart-fallback |
| `X3` | References | Tried: subdomain-servername-concatenation |
| `X4` | References | Tried: dynamic-format-list-based |
| `X5` | References | Tried: fallback-chain-edge-cases |
| `X6` | References | Tried: conditional-domain-column |
| `X7` | References | Tried: sort-by-domain-rule-level |
| `X8` | References | Tried: sort-by-domain-row-level |
| `X9` | References | Tried: complete-domain-column-integration |
| `X10` | References | Tried: domain-column-always-display |
| `X11` | References | Tried: url-for-based-domain-extraction |
| `X12` | References | Tried: conditional-subdomain-column-after-rule |
| `X13` | References | Tried: conditional-host-column-after-rule |
| `X14` | References | Tried: auto-detect-subdomain-or-host-column |
| `X15` | References | Tried: dynamic-column-count-with-list-building |
| `X16` | References | Sources consulted for column domain rule |


















## Instructions

### I1 — How to evaluate a change to column domain rule

Figure of merit: **subdomain_column_present** (max, target 1.0).

Measured by: Binary check: run `flask routes` command programmatically and verify that (1) output contains a "Domain" or "Subdomain" column header, (2) subdomain values are correctly shown for routes registered with subdomain parameter, (3) the full domain (subdomain.SERVER_NAME or just SERVER_NAME) is displayed in the new column. Score 1.0 if all three conditions met, 0.0 otherwise.

Cases differ along: route_type, server_name_set, subdomain_type.

## Rules

## References

### X1 — Tried: add-domain-column-full

Add a "Domain" column showing full domain (subdomain.SERVER_NAME) for each route

**Hypothesis**: Adding a Domain column that combines rule.subdomain with current_app.config['SERVER_NAME'] will display full domain info as requested in issue. Falsified if: (1) rule.subdomain is not accessible, (2) SERVER_NAME combination logic doesn't match Flask's URL generation, or (3) output format breaks existing parsing tools.

**Status**: potential (train 1/1). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: add-domain-column-smart-fallback

Add Domain column with conditional logic handling all SERVER_NAME/subdomain combinations

**Hypothesis**: Add Domain column with smart fallback: show full domain (subdomain.SERVER_NAME) when both exist, show subdomain alone if no SERVER_NAME, show SERVER_NAME alone if no subdomain, show '-' if neither. Falsified if: logic becomes too complex, edge cases still fail, or users prefer simpler display.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: subdomain-servername-concatenation

Combine rule.subdomain with SERVER_NAME config using pattern: subdomain.SERVER_NAME when both present, with fallbacks to either value alone or '-' when missing. Preserves ports and nested subdomains.

**Hypothesis**: The combination pattern subdomain.SERVER_NAME matches Flask's actual routing behavior and will correctly display full domain information for routes with subdomains.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: dynamic-format-list-based

Refactor routes_command to use list-based row building with dynamic format string generation, enabling variable column count. Changes: headers tuple→list, collect rows as lists, calculate widths dynamically, build format string with join. Handles conditional domain column cleanly.

**Hypothesis**: Converting from hardcoded 3-column format to dynamic list-based row building allows adding a 4th domain column conditionally without breaking existing output. The format string pattern can be generated dynamically using join of format parts.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: fallback-chain-edge-cases

Implement 4-level fallback: (1) subdomain + SERVER_NAME → 'subdomain.SERVER_NAME', (2) subdomain only → 'subdomain', (3) SERVER_NAME only → 'SERVER_NAME', (4) neither → '-'. Handles nested subdomains, ports, wildcards, and None/empty values.

**Hypothesis**: A fallback chain (both→subdomain-only→servername-only→placeholder) handles all edge cases including missing values, empty strings, and dynamic patterns without errors.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: conditional-domain-column

Domain column displayed only when at least one route has domain info (subdomain or host). Prevents breaking existing apps without domain routing. No user flag needed - automatic detection based on route content.

**Hypothesis**: Using conditional display (has_domain check) instead of always showing domain column maintains backward compatibility. Column only appears when any(rule.host or rule.subdomain), keeping output clean for apps without domain routing.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: sort-by-domain-rule-level

Add "domain" to sort choices (line 992). Sort rules before row building using lambda accessing rule.host or rule.subdomain based on host_matching flag. Empty/None domains sort first via 'or ""' fallback. Maintains consistency with existing endpoint/methods/rule sorting approach.

**Hypothesis**: Adding "domain" to sort choices and sorting rules by (rule.host if host_matching else rule.subdomain) before building rows maintains the current sorting architecture while enabling domain sorting. None values handled with 'or ""' to sort empty domains first.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: sort-by-domain-row-level

REFUTED: Sorting rows after building with itemgetter. Reason: More invasive than sorting rules before building. Current code sorts rules before processing; maintaining that pattern is cleaner. Would require new import and restructuring all sorting logic. The simpler approach of sorting rules with la

**Hypothesis**: Sorting rows (lists) after building using itemgetter would enable domain sorting but requires refactoring the entire sorting flow and importing itemgetter.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Tried: complete-domain-column-integration

Complete integration: conditional domain column with dynamic formatting, subdomain+SERVER_NAME combination with 4-level fallback, domain sorting support. Refactors routes_command to list-based row building enabling variable column count. Column appears only when routes have domain info (automatic de

**Hypothesis**: Integrating conditional display + dynamic formatting + smart fallback + domain sorting into one complete implementation will satisfy all requirements in issue #5063. Falsified if: (1) integration creates conflicts between the individual approaches, (2) implementation is more complex than modular approaches, (3) testing reveals edge cases not covered by the integration, or (4) performance degrades 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X10 — Tried: domain-column-always-display

Always show 4th Domain column in routes output, displaying '-' or empty string for routes without domain information. Simpler implementation than conditional display (no has_domain check needed), provides fixed column count for script parsing, but shows empty column for apps without subdomain routin

**Hypothesis**: Always displaying the domain column (even when all values are empty/'-') provides consistent output format regardless of subdomain usage, making the command output parseable by scripts that expect fixed column count. Falsified if: (1) users find empty columns visually cluttered, (2) existing tools break due to unexpected 4th column when they expected 3, or (3) the benefit of consistency doesn't ou

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X11 — Tried: url-for-based-domain-extraction

Extract domain by calling Flask's url_for(_external=True) for each route and parsing the domain from the generated URL. Guarantees displayed domain matches Flask's actual behavior, handles all edge cases automatically through Flask's own logic, but may require request context simulation and has high

**Hypothesis**: Using Flask's url_for with _external=True to generate the full URL for each route, then parsing the domain from that URL, ensures the displayed domain exactly matches Flask's actual URL generation behavior including all edge cases. Falsified if: (1) url_for requires a request context which routes command doesn't have, (2) url_for doesn't work for all rule types (e.g., with converters), (3) perform

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X12 — Tried: conditional-subdomain-column-after-rule

Add "Subdomain" column as 4th column (after Endpoint, Methods, Rule) only when any route has a subdomain. Display subdomain.SERVER_NAME when both exist, subdomain alone if no SERVER_NAME, or '-' if no subdomain.

**Hypothesis**: Adding "Subdomain" as the 4th column (keeping Endpoint first) satisfies both the target test requirement for "Subdomain" header and the existing test requirement for endpoint-at-position-0. Falsified if: (1) target tests expect it in a different position, (2) conditional display breaks when no subdomains exist, or (3) the column ordering is rejected by tests.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X13 — Tried: conditional-host-column-after-rule

Add "Host" column as 4th column (after Endpoint, Methods, Rule) only when host_matching is enabled. Display rule.host value or '-' if host is None.

**Hypothesis**: Adding "Host" column (not "Subdomain") when host_matching is enabled satisfies the target test requirement for "Host" in result.output while maintaining endpoint-first ordering. Falsified if: (1) host_matching detection fails, (2) both Host and Subdomain columns are needed simultaneously, or (3) rule.host value format doesn't match expected display.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X14 — Tried: auto-detect-subdomain-or-host-column

Automatically detect whether to add "Subdomain" or "Host" column (not both) as 4th column based on app.url_map.host_matching flag and presence of subdomains in routes. Keep Endpoint first to preserve test compatibility.

**Hypothesis**: Detecting whether to show "Subdomain" or "Host" column based on app configuration (host_matching vs subdomain usage) provides correct header for both modes. The logic: if host_matching, show "Host" column; elif any(rule.subdomain), show "Subdomain" column; else show neither. Falsified if: (1) both columns needed simultaneously, (2) detection logic fails, or (3) tests expect both headers present.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X15 — Tried: dynamic-column-count-with-list-building

Build headers, widths, and rows as lists that conditionally include 4th column, then convert to tuples for formatting. Keeps existing 3-column format when no subdomain/host info exists.

**Hypothesis**: Using dynamic tuple building for headers/widths/format-string (instead of fixed 3-column tuples) allows conditional 4th column without duplicating format logic. When subdomain/host column is needed, extend tuples to 4 elements; when not needed, keep 3 elements. Falsified if: (1) format string generation fails with variable column counts, (2) width calculation breaks, or (3) row iteration complexit

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X16 — Sources consulted for column domain rule

- Alternative domain resolution approach considered against direct rule.subdomain + SERVER_NAME combination (from server-name-combination-findings.md). Flask url_for documentation and SERVER_NAME docume
- Analysis comparing rule-level vs row-level sorting. Considered upstream PR pattern but found rule-level sorting simpler for this codebase.
- Analysis of current cli.py implementation and testing of has_domain detection logic. Pattern matches upstream PR design philosophy.
- Attempt 1 failure analysis showing Endpoint must be first; skill flask-routes-cli R1 and R2; issue.md lines 36-42 showing expected output format
- Combined edge case analysis with issue requirements
- Flask 2.3 config docs (https://flask.palletsprojects.com/en/2.3.x/config/), tests/test_basic.py lines 1436-1478 (test_server_name_subdomain), src/flask/blueprints.py lines 380-390 (nested subdomain co
- Issue example line 36-41, Flask SERVER_NAME documentation, current routes_command implementation
- src/flask/blueprints.py lines 380-390, tests/test_basic.py subdomain tests, Flask 2.3 config docs
