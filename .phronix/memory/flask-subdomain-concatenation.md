---
name: flask-subdomain-concatenation
description: Flask blueprint nested subdomain concatenation pattern and display rules
metadata:
  type: reference
---

**What:** How Flask concatenates nested blueprint subdomains.

**Pattern:** Parent subdomain + "." + child subdomain

**Code location:** src/flask/blueprints.py lines 380-390

**Logic:**
```python
if state.subdomain is not None and bp_subdomain is not None:
    bp_options["subdomain"] = bp_subdomain + "." + state.subdomain
elif bp_subdomain is not None:
    bp_options["subdomain"] = bp_subdomain
elif state.subdomain is not None:
    bp_options["subdomain"] = state.subdomain
```

**Result:** Nested blueprints produce multi-level subdomains like "api.v1" or "<internal-host>"

**Display implications:** 
- When combined with SERVER_NAME, preserve the full nested subdomain: "api.v1.example.com"
- The rule.subdomain attribute contains the full concatenated string
- Do not attempt to parse or re-combine the subdomain; it's already complete

**Why this matters:** CLI commands displaying route information must show the subdomain as-is to match actual routing behavior

**Related:** [[flask-server-name-format]] for SERVER_NAME format
