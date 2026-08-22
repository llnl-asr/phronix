---
name: flask-routes-domain-column-fix
description: Implemented Domain column in Flask routes CLI
metadata:
  type: project
---

---
name: flask-routes-domain-column-fix
description: Updated Flask routes CLI to include Domain column, compute safely, adjust output formatting.
metadata:
  type: project
---

**Why:** The routes command lacked a Domain column, causing failures and TypeError when SERVER_NAME is None.
**How to apply:** Modify `src/flask/cli.py` in the `routes_command` function to:
- Compute a `domains` list handling missing `SERVER_NAME` or `subdomain` by defaulting to empty string.
- Update `headers` to include "Domain" as the first column.
- Adjust `widths` to account for the new column.
- Change the row format string to have four placeholders.
- Output rows using the domain value.

**Related memory:** [[flask-routes-domain-column]]
