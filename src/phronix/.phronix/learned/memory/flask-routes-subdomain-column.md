---
name: flask-routes-subdomain-column
description: Flask routes command already shows subdomain column when subdomains are used
metadata:
  type: project
---

The `flask routes` CLI command in Flask already includes logic to display a subdomain (or host) column when any rule has a subdomain. It determines `has_domain` and adds a column header accordingly. Therefore, adding a subdomain column does not require code changes; ensure that blueprints are registered with a `subdomain` parameter and that `SERVER_NAME` is configured.

**Why:** This avoids unnecessary modifications and leverages existing functionality.
**How to apply:** Define blueprints with the `subdomain` argument and set `app.config['SERVER_NAME']` to the base domain. Then run `flask routes` to see the subdomain column.
