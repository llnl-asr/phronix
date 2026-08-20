---
name: python-assert-vs-valueerror-validation
description: Use ValueError for input validation, never assert - asserts disabled with python -O, proper for API contracts not debugging
metadata:
  type: feedback
---

**Why:** Input validation must use `raise ValueError()`, NOT `assert`:

1. **Production safety**: `assert` statements are disabled with `python -O` optimization flag
2. **API contract**: ValueError is the proper exception type for invalid parameter values
3. **Best practice**: Assertions are for debugging/testing internal invariants, not validating user input
4. **Consistency**: Python stdlib and frameworks use ValueError for parameter validation

**How to apply:**
```python
# WRONG - disabled in optimized mode:
assert "." not in name, "Name should not contain dots"

# CORRECT - always enforced:
if "." in name:
    raise ValueError("'name' may not contain a dot '.' character.")
```

**Evidence:** Flask PR #4045 changed ALL three validations (name, endpoint, view_func) from assert to ValueError for this reason. Current code at blueprints.py:364, 366-368 uses assert (pre-PR state).

**Links:** [[flask-blueprint-dot-separator-semantics]] [[flask-endpoint-validation-valueerror]]
