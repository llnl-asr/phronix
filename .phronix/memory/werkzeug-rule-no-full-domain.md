---
name: werkzeug-rule-no-full-domain
description: Werkzeug Rule objects have no built-in full domain property; manual combination required
metadata:
  type: reference
---

**What was searched for:** Built-in method or property on Werkzeug Rule objects to automatically get full domain.

**What was found:** None exists. The combination must be implemented manually.

**Attributes that DO NOT exist on Rule objects:**
- No `rule.domain` attribute
- No `rule.full_host` attribute  
- No `rule.qualified_domain` attribute
- No method to automatically combine subdomain + SERVER_NAME

**What DOES exist:**
- `rule.subdomain` - returns string or None (subdomain portion only)
- `rule.host` - returns string or None (for host_matching mode, mutually exclusive with subdomain)

**Why this matters:** 
- Cannot rely on Werkzeug to provide full domain
- Must implement combination logic in application code
- Must access SERVER_NAME from Flask's config separately
- The fallback chain must be explicit

**Implication for implementation:** Any CLI command or debugging tool that needs to display full domain information must implement the combination logic itself using the pattern in [[flask-domain-display-pattern]].

**Verified in:** Werkzeug 3.1.8 documentation at https://werkzeug.palletsprojects.com/en/stable/routing/, direct attribute inspection of Rule objects

**Related:** [[flask-domain-display-pattern]] [[flask-subdomain-concatenation]]
