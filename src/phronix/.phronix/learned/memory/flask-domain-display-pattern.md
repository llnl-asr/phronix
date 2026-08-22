---
name: flask-domain-display-pattern
description: Correct fallback pattern for combining Flask rule.subdomain with SERVER_NAME config
metadata:
  type: feedback
---

**What:** Correct pattern for combining Flask route subdomain with SERVER_NAME for display.

**Why:** Route display commands need to show full domain information. Subdomains are relative and SERVER_NAME provides the base domain. The combination must match Flask's actual routing behavior.

**Pattern:**
```python
def format_domain(rule, server_name):
    subdomain = rule.subdomain
    
    # Both present: concatenate
    if subdomain and server_name:
        return f"{subdomain}.{server_name}"
    
    # Only subdomain: partial info
    if subdomain:
        return subdomain
    
    # Only SERVER_NAME: base domain  
    if server_name:
        return server_name
    
    # Neither: indicate unavailable
    return "-"
```

**How to apply:**
1. Get SERVER_NAME from `current_app.config.get("SERVER_NAME")`
2. For each rule, access `rule.subdomain` (may be None, string, or empty string)
3. Apply the 4-level fallback shown above
4. Treat empty string subdomain same as None
5. Preserve nested subdomains (e.g., "api.v1") as-is
6. Preserve ports from SERVER_NAME (e.g., "dev.local:5000" remains intact)
7. Preserve dynamic patterns like "<user>" in subdomain wildcards

**Edge cases:**
- Nested subdomains: "api.v1" + "example.com" → "api.v1.example.com"
- With port: "admin" + "dev.local:5000" → "admin.dev.local:5000"  
- Wildcard: "<user>" + "example.com" → "<user>.example.com"
- No SERVER_NAME: "admin" + None → "admin"
- No subdomain: None + "example.com" → "example.com"
- Neither: None + None → "-"

**Verified:** tests/test_basic.py test_server_name_subdomain (lines 1436-1478), src/flask/blueprints.py subdomain concatenation (lines 380-390)

**Related:** [[flask-server-name-format]] [[flask-subdomain-concatenation]]
