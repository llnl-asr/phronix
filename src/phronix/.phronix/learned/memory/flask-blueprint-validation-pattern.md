---
name: flask-blueprint-validation-pattern
description: Flask Blueprint input validation pattern: use ValueError in __init__ not registration, following fail-fast principle
metadata:
  type: reference
---

**Flask Blueprint validation pattern: ValueError in __init__ for input validation**

Flask Blueprint name validation happens in `Blueprint.__init__`, not at registration time.

**Why validation in __init__:**

1. **Fail-fast principle**: Invalid input rejected immediately when Blueprint is created, not deferred to registration
2. **Blueprints register multiple times**: A blueprint can be registered with multiple applications or multiple times with the same app (evidenced by `_got_registered_once` flag and comments at lines 50-53)
3. **Name is fundamental to identity**: Used immediately in string operations throughout the class
4. **Nested blueprints**: Flask 2.0 supports nested blueprints; validation at registration would delay child validation until parent registration

**Exception type: ValueError, not AssertionError**

- **ValueError**: For invalid input parameters (user-facing, wrong usage)
- **AssertionError**: For internal invariants and application state checks (e.g., blueprint collision at lines 271-277)

Upstream PR #4045 consistently uses ValueError for input format validation.

**Pattern to follow:**
```python
def __init__(self, name: str, ...):
    super().__init__(...)
    
    if "." in name:
        raise ValueError("'name' may not contain a dot '.' character.")
    
    self.name = name
    ...
```

Validation occurs BEFORE assignment to self.name.

**Source:** PR #4045
**Related:** [[flask-blueprint-dot-separator-semantics]]
