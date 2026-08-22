---
name: flask-blueprint-name-validation
description: Disallow dots in blueprint names using explicit check, not assert.
metadata:
  type: project
---

**Why:** Using `assert` for input validation can be disabled with the `-O` flag and raises `AssertionError`, which may not match expected error types. This caused test failures for blueprint name validation.
**How to apply:** Replace `assert '.' not in name, 'Blueprint name should not contain dots'` with:
```python
if '.' in name:
    raise ValueError('Blueprint name must not contain dots')
```
This ensures validation always runs and raises a consistent exception.

[[flask-blueprint-name-validation]]
