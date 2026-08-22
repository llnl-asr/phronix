---
name: flask-4045-implementation
description: Flask issue #4045 fix: blueprint name dot validation implementation and rationale
metadata:
  type: lesson
---

**Task**: pallets__flask-4045 - Add validation to raise error when blueprint name contains a dot.

**Context**: Flask 2.0 introduced nested blueprints where dots serve as structural separators in the naming hierarchy (e.g., `parent.child.endpoint`). The issue noted that "An error was already added for endpoint names in 1.0, but should have been added for [blueprint names] as well."

**Solution implemented**: Added ValueError validation in `Blueprint.__init__()` in `src/flask/blueprints.py` after the `super().__init__()` call but before the `self.name` assignment:

```python
if "." in name:
    raise ValueError("'name' may not contain a dot '.' character.")
```

**Why this approach**:
- **ValueError** (not AssertionError) - correct exception type for invalid user input parameters
- **Location in __init__** - fail-fast principle, validates at creation time, not registration
- **Simple containment check** - `"." in name` handles all edge cases correctly
- **Message format** - matches Flask's error message conventions from upstream PR #4045

**Verified**: Manual testing confirmed ValueError is raised for any blueprint name containing a dot (including edge cases like leading/trailing/multiple dots), while valid names work correctly.

**Related**: [[flask-blueprint-validation-pattern]], [[flask-blueprint-dot-separator-semantics]], [[flask-blueprint-name-validation#L1]]
