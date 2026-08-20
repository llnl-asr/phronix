---
name: flask-routes-subdomain-validated-approach
description: Flask routes subdomain/host display: validated working implementation (attempt 2 success)
metadata:
  type: project
---

**Status:** RESOLVED (2/2 target tests pass, 54/54 regression tests pass)

**Working approach:** Auto-detect conditional column (approach X14 from flask-routes-subdomain-display)

**Implementation location:** `src/flask/cli.py` function `routes_command` (lines 1018-1078 in successful diff)

**Key validated decisions:**
1. Conditional column display: Show only when `host_matching` enabled OR any route has subdomain
2. Header names: "Host" for host_matching mode, "Subdomain" for subdomain mode (NOT generic "Domain")
3. Column position: 4th position (after Endpoint, Methods, Rule) - Endpoint MUST stay first
4. Subdomain display: Combine `rule.subdomain` with `SERVER_NAME` to show full domain (e.g., "admin.test.local")
5. Host display: Use `rule.host or "-"`
6. Backward compatibility: When no domains, output unchanged (3-column format preserved)

**Why this succeeded where others failed:**
- Endpoint-first preserves test compatibility (tests use `expect_order()` on line prefixes)
- Proper header naming satisfies literal string checks in test_subdomain and test_host
- Conditional display maintains clean output and backward compatibility
- Auto-detection handles both modes without user flags

**Corrector:** Flask test suite itself (tests/test_cli.py::TestRoutes::test_subdomain, test_host)

**References:** See [[flask-routes-subdomain-display#L1]], [[flask-routes-subdomain-display#I3]], [[flask-routes-subdomain-display#R1]], [[flask-routes-subdomain-display#R2]]
