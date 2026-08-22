---
name: flask-routes-domain-column
description: When adding a Domain column to Flask routes CLI, update header tuple and row format to include four columns and safely compute domain to avoid None causing TypeError/ValueError.
metadata:
  type: project
---

Header = ("Domain", "Endpoint", "Methods", "Rule"). Compute domains list handling missing SERVER_NAME or subdomain, default to empty string. Adjust widths calculation to include domain column. Ensure row format string has four placeholders.
