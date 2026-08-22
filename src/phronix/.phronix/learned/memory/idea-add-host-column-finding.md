---
name: idea-add-host-column-finding
description: Finding for add-host-column idea in flask routes
metadata:
  type: reference
---

The current Flask CLI `routes` command already includes a `Domain` column when `host_matching` is enabled. A minimal app with `HOST_MATCHING=True` and a subdomain blueprint shows the expected output:
```
Domain            Endpoint          Methods  Rule
admin.test.local  admin.admin_home  GET      /home
...```
Thus the requested feature is already present; no code changes are required.

**Why:** The implementation in `src/flask/cli.py` computes `host_matching` and uses `_domain` to select `rule.host` or `rule.subdomain` for the column.
**How to apply:** Ensure the Flask app has `HOST_MATCHING=True` (or `app.config['HOST_MATCHING'] = True`). The `flask routes` command will then display the domain column.
