---
name: pallets-flask-5063-propose-solution
description: Proposed solution to add Domain column to flask routes output
metadata:
  type: project
---

---
name: pallets-flask-5063-propose-solution
description: Proposed solution to add Domain column to flask routes output
metadata:
  type: project
---
The research propose stage identified that the Flask CLI `routes` command does not display which subdomain each route belongs to. A fix is to modify the `flask/cli.py` implementation of the `routes` command to compute a domain string for each rule based on the app's `SERVER_NAME` configuration and the rule's `subdomain` attribute.

**Why:** Users need to see domain/subdomain information directly in the `flask routes` output to understand routing configuration without inspecting blueprint registrations.

**How to apply:** Update the helper that builds the table of routes (`get_rule_domain`) to return a domain string (e.g., `admin.test.local`) when `host_matching` is false and `subdomain` is set, otherwise fall back to the existing behavior. Add a new column header "Domain" to the CLI output and include the computed domain for each rule.

[[aspect-record-ignore-paths-parsing]]
