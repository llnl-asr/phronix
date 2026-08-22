# Lessons — flask-routes-domain

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Test environment missing pytest prevents verification

**2026-08-21** — The harness could not run target tests because pytest is unavailable, leading to false failure reports. Ensure pytest is installed in the environment before validating route domain changes.

### L2 — Added Domain column to Flask routes output via get_rule_domain helper

**2026-08-21** — Implemented get_rule_domain(rule) to compute a domain string based on subdomain and SERVER_NAME when host_matching is disabled, and updated routes_command to display a "Domain" column. This change mirrors Flask's CLI behavior and makes subdomain information visible in `flask routes` output.
