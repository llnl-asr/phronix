---
name: flask-server-name-format
description: Flask SERVER_NAME config format and behavior for subdomain matching
metadata:
  type: reference
---

**What:** Flask's SERVER_NAME configuration parameter format and requirements.

**Format:** "domain.tld" or "domain.tld:port" (e.g., "example.com" or "dev.local:5000")

**Key behaviors:**
- Required for subdomain_matching to work correctly
- Can include port numbers which are preserved in URL generation
- Default value is None if not configured
- Changed in Flask 2.3: no longer affects SESSION_COOKIE_DOMAIN
- Changed in Flask 1.0: does not implicitly enable subdomain_matching

**Source:** Flask 2.3 configuration documentation at https://flask.palletsprojects.com/en/2.3.x/config/

**Verified in:** Flask 2.3 (base commit 182ce3dd15df), tests/test_basic.py test_server_name_subdomain function (lines 1436-1478)

**Related:** [[flask-subdomain-concatenation]] for how subdomains combine with SERVER_NAME
