---
name: flask-4045-three-validations
description: Flask PR #4045 updated three validations (name, endpoint, view_func) from assert to ValueError for consistency
metadata:
  type: reference
---

**Why:** Upstream PR #4045 changed THREE validations for consistency, not just the blueprint name. All changed from assert to ValueError.

**Three validations in blueprints.py:**

1. **Blueprint name** (in `__init__`, ~line 190):
   ```python
   if "." in name:
       raise ValueError("'name' may not contain a dot '.' character.")
   ```

2. **Endpoint** (in `add_url_rule`, ~line 364):
   ```python
   # OLD: assert "." not in endpoint, "Blueprint endpoints should not contain dots"
   # NEW:
   if endpoint and "." in endpoint:
       raise ValueError("'endpoint' may not contain a dot '.' character.")
   ```

3. **View function** (in `add_url_rule`, ~lines 366-368):
   ```python
   # OLD: assert "." not in view_func.__name__, "Blueprint view function name should not contain dots"
   # NEW:
   if view_func and hasattr(view_func, "__name__") and "." in view_func.__name__:
       raise ValueError("'view_func' name may not contain a dot '.' character.")
   ```

**How to apply:** When backporting PR #4045, update all three validations for consistency. The endpoint and view_func validations add defensive checks (existence, hasattr) before validation.

**Links:** [[flask-endpoint-validation-valueerror]] [[python-assert-vs-valueerror-validation]] [[flask-4045-error-message-format]]
