---
name: subdomain
description: Research on subdomain. Covers how does Flask store/expose a per-rule subdomain today — is it available directly on werkzeug Rule objects (rule.subdomain) as registered, and does it need combining with app.config['SERVER_NAME'] to form a full domain, or is there an existing helper (e.g. in url_map or app) that already resolves full domains per rule; what exact column name, ordering, and header formatting should the new domain/subdomain output use to match maintainers' likely acceptance criteria — should it be a new column always shown, or only shown when --sort domain or a new flag is passed, a
subject: subdomain
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to subdomain |
| `I2` | Instructions | How to solve subdomain |
| `X1` | References | Where research on this subject stands |





























































































































## Instructions

### I1 — How to evaluate a change to subdomain

Figure of merit: **routes_command_domain_correctness** (max, target 1.0).

Measured by: Fraction of corpus instances where running `flask routes` (via CliRunner.invoke on a Flask app with SERVER_NAME set and blueprints/rules registered with varying subdomains) produces output whose Domain/Subdomain column (or equivalent per-rule domain value) exactly matches the expected fully-qualified subdomain for every rule, AND existing routes_command behavior (endpoint/methods/rule columns, sor

Cases differ along: server_name_config, sort_option, static_route, subdomain_presence.

### I2 — How to solve subdomain

Try these in order, ONE at a time. Ranked by measured **routes_command_domain_correctness** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A3` **domain-column-first-position-always-shown** — routes_command_domain_correctness 0.000, potential — Add a "Domain" column as the FIRST column (before Endpoint) in `flask routes` output, show
2. `A1` **manual_domain_concat_subdomain_server_name** — routes_command_domain_correctness unmeasured, potential — Build full domain per rule manually in flask/cli.py routes_command by combining rule.subdo
3. `A2` **use_existing_full_domain_helper** — routes_command_domain_correctness unmeasured, potential — Hypothesized that werkzeug or Flask already exposes a helper that, given a single Rule and

...and 8 lower-ranked approach(es); see `research_rank`.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **routes_command_domain_correctness** (max, target 1.0).

**Established**
- use_existing_full_domain_helper (potential)
- domain-column-first-position-always-shown (working routes_command_domain_correctness=0.0)
- domain_column_verified_concat_with_none_guard (potential)

**Still open**
- manual_domain_concat_subdomain_server_name (potential)
- domain_column_fallback_to_server_name (potential)
- domain-value-subdomain-plus-server-name (potential)
- domain_column_naive_string_concat (potential)
- add-sort-domain-choice (potential)
- check_subdomain_is_none (potential)

**Where the detail is**
- manual_domain_concat_subdomain_server_name: werkzeug/routing/rules.py Rule.__init__ (~458-484) and Rule.bind (~570-578); werkzeug/routing/map.py MapAdapte
- use_existing_full_domain_helper: grep of "subdomain"/"domain"/"host_matching" across werkzeug/routing/rules.py, werkzeug/routing/map.py, src/fl
- domain-column-first-position-always-shown: issue.md (GitHub issue "Flask routes to return domain/sub-domains information") — explicit before/after sample
- domain_column_fallback_to_server_name: Derived from src/flask/app.py create_url_adapter (~line 1874-1912) and url_for (~line 1678-1686) behavior; rou

...and 3 more line(s); see the full record.