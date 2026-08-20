---
name: flask-4045-error-message-format
description: Flask PR #4045 error message format: "'parameter' may not contain a dot '.' character." with specific formatting conventions
metadata:
  type: reference
---

**Why:** Upstream Flask PR #4045 establishes a consistent error message format for parameter validation.

**Pattern:** `"'<parameter>' may not contain a dot '.' character."`

**Elements:**
- Parameter name in single quotes: `'name'`, `'endpoint'`, `'view_func'`
- Lowercase "may not"
- Explicit character description: `a dot '.' character`
- Trailing period

**Examples from PR #4045:**
```python
raise ValueError("'name' may not contain a dot '.' character.")
raise ValueError("'endpoint' may not contain a dot '.' character.")
raise ValueError("'view_func' name may not contain a dot '.' character.")
```

**How to apply:** When adding validation that matches upstream merged PRs, use their exact error message format for consistency with the version the fix will be merged into.

**Links:** [[flask-endpoint-validation-valueerror]] [[flask-blueprint-dot-separator-semantics]]
