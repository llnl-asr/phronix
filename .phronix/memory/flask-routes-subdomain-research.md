---
name: flask-routes-subdomain-research
description: Research completed for Flask routes CLI subdomain display enhancement (issue 5063)
metadata:
  type: project
---

**What:** Researched how to add subdomain/domain information to `flask routes` command output.

**Finding:** Werkzeug Rule objects have `.subdomain` attribute. Flask's SERVER_NAME config provides base domain. Solution is to add a "Domain" column showing `subdomain.SERVER_NAME` for routes with subdomains.

**Skill created:** [[column-domain]] in project layer - contains ranked approaches, investigated aspects, and sources.

**Implementation location:** `src/flask/cli.py`, function `routes_command` (lines 1001-1034)

**Recommended approach:** add-domain-column-full (scored 1.0 on figure of merit)
- Add Domain column as first column
- Build domain string: `subdomain.SERVER_NAME` when both present, with fallbacks
- Extend existing table formatting from 3 to 4 columns

**Key edge cases:**
- No SERVER_NAME set: show subdomain only or "-"
- No subdomain: show SERVER_NAME or "-"
- Nested subdomains: preserve as-is

**Test corpus:** 9 instances covering subdomain_type × route_type × server_name_set (stratified into train/validate/test)

**Why this approach:** Issue explicitly requests showing "which routes for which subdomain" with example output showing full domains like "admin.test.local". User wants clarity without checking configuration.

**How to apply:** Load skill with `phronix_skill_load(name="column-domain")` and follow I2. Implementation guide in tmp/research/IMPLEMENTATION_GUIDE.md shows exact code changes needed.
