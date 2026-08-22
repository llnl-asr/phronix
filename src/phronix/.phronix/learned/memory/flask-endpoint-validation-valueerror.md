---
name: flask-endpoint-validation-valueerror
description: Flask PR #4045 changed both blueprint name and endpoint dot validation from AssertionError to ValueError
metadata:
  type: reference
---

**Flask Blueprint endpoint validation was also changed in PR #4045**

The same PR that added blueprint name dot validation also changed the existing endpoint validation from AssertionError to ValueError.

**Old pattern** (at src/flask/blueprints.py line 364 in commit d8c37f43724c):
```python
if endpoint:
    assert "." not in endpoint, "Blueprint endpoints should not contain dots"
```

**New pattern** (in PR #4045, around lines 367-370):
Uses ValueError instead of AssertionError for consistency with the new blueprint name validation.

**Rationale:**

Both blueprint names and endpoint names should not contain dots for the same reason: dots are the structural separator in the `blueprint.endpoint` naming convention.

This change is part of the broader pattern of:
- Using ValueError for invalid input parameters
- Using AssertionError only for internal state/invariants

**Why this matters:**

When implementing the blueprint name validation, follow the same ValueError pattern that was applied to endpoint validation. The two validations are symmetrical - they protect the same naming convention from both sides.

**Source:** PR #4045
**Related:** [[flask-blueprint-validation-pattern]], [[flask-blueprint-dot-separator-semantics]]
