---
name: pallets-flask-5063
description: The pallets-flask-5063 subject.
subject: pallets-flask-5063
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I1 – Add utility to list subdomain routes |
| `I2` | Instructions | I2 – Implement subdomain route listing utility |
| `I3` | Instructions | Problem it solves |
| `I4` | Instructions | Key idea |
| `I5` | Instructions | Step 1 – Add email attribute to custom user model |
| `R1` | Rules | R1 – Subdomain routing isn\'t shown by flask routes output |







## Instructions

### I1 — I1 – Add utility to list subdomain routes

Add a helper function `list_subdomain_routes(app)` that iterates over `app.url_map.iter_rules()` and prints each rule together with its subdomain. This aids developers in verifying which endpoints belong to which subdomains.

```python
def list_subdomain_routes(app):
    """Return a mapping of subdomains to their registered routes.
    Returns a dict where keys are subdomain strings (empty string for the main domain) and values are lists of strings
    ``"<endpoint> -> <rule>"``.
    """
    routes_by_subdomain: dict[str, list[str]] = {}
    for rule in app.url_map.iter_rules():
        sd = rule.subdomain or '(no subdomain)'
        routes_by_subdomain.setdefault(sd, []).append(f"{rule.endpoint} -> {rule.rule}")
    return routes_by_subdomain
```

You can call this function in the Flask shell or a test suite to produce a clear view of which routes are attached to each subdomain.

Example usage in a Flask app context:
```python
from utils.routes import list_subdomain_routes

with app.app_context():
    mapping = list_subdomain_routes(app)
    for subdomain, routes in mapping.items():
        print(f"Subdomain: {subdomain}")
        for r in routes:
            print(f"  {r}")
```

This resolves the issue where `flask routes` does not display subdomain assignments.

### I2 — I2 – Implement subdomain route listing utility

Create a new module `utils/routes.py` containing the `list_subdomain_routes(app)` function as described in the task. This function iterates over `app.url_map.iter_rules()`, groups routes by their `rule.subdomain` (using '(no subdomain)' for the default), and returns a dictionary mapping subdomain strings to lists of ``"<endpoint> -> <rule>"`` strings.

Add a test in `tests/test_routes.py` that creates a Flask app with at least two blueprints registered under different subdomains, invokes `list_subdomain_routes(app)`, and asserts that the returned dictionary contains the expected subdomains and routes.

Update any documentation or README to reference the new utility.

### I3 — Problem it solves

Custom user model missing an `email` attribute leads to `TypeError` in Flask Pallets benchmark when code expects a string email.

### I4 — Key idea

The custom user model must expose the email field under the expected name; adding a `email` attribute or an alias resolves the TypeError in token generation.

### I5 — Step 1 – Add email attribute to custom user model

Edit the custom user model file (e.g., `app/models.py`) to include `email = db.Column(db.String(255), nullable=False, default='' )` ensuring it stores a string email.

```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # existing fields
+    email = db.Column(db.String(255), nullable=False, default='')
```

## Rules

### R1 — R1 – Subdomain routing isn\'t shown by flask routes output

Do not rely on the output of `flask routes` to determine which routes belong to which subdomain. Flask’s built‑in `flask routes` command omits the subdomain column, so the mapping of routes to subdomains is lost. Instead, use Flask’s routing map to retrieve subdomain information:

```python
from flask import Flask

def list_subdomain_routes(app: Flask) -> dict[str, list[str]]:
    """Return a dict mapping each subdomain to its routes.
    The key is the subdomain string (empty for the main domain)."""
    subdomain_routes = {}
    for rule in app.url_map.iter_rules():
        sd = rule.subdomain or '(no subdomain)'
        subdomain_routes.setdefault(sd, []).append(f"{rule.endpoint} -> {rule.rule}")
    return subdomain_routes
```

Use this helper in development tools or tests to verify that each blueprint is registered under the intended subdomain.

## References

- `skill_load(name="pallets-flask-5063", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

