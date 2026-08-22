---
name: blueprint-name-dot-check
description: Missing validation for dot in blueprint name during registration
metadata:
  type: feedback
---

**Problem:** In `src/flask/blueprints.py`, the `Blueprint.register` method validates that endpoint names and view function names do not contain dots, but does not validate the blueprint's own `name` attribute. This can lead to ambiguous endpoint prefixes when nested blueprints use dot-containing names, as the registration process concatenates `self.name` to endpoint keys.

**Proposed Fix:** Add a check at the start of `Blueprint.register` to raise an `AssertionError` if `'.'` is present in `self.name`. Example:
```python
if '.' in self.name:
    raise AssertionError('Blueprint name should not contain dots')
```
Insert this before checking `if self.name in app.blueprints:` to prevent registration of improperly named blueprints.

**Why:** Ensures uniqueness of blueprint identifiers and prevents subtle routing bugs when nested blueprints generate endpoint names like `parent.child.view`. Matching the existing rule for endpoint names maintains consistency.

**How to apply:** Create a new capability script using `add_check_dot_to_blueprint_register`, then execute it or apply via the project’s tooling. After applying, run the full test suite to confirm no regressions.

**Next Steps:** Implement the check, run relevant tests (e.g., blueprint routing tests), and verify that dot-containing blueprint names now raise an error.
