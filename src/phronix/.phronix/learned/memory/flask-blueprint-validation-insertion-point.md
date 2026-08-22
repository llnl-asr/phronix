---
name: flask-blueprint-validation-insertion-point
description: Flask Blueprint.__init__() validation placement: after super().__init__() line 190, before self.name assignment line 191
metadata:
  type: reference
---

**Why:** Validation must occur AFTER `super().__init__()` but BEFORE using the parameter, following fail-fast principle.

**Location in Flask blueprints.py Blueprint.__init__():**
- After line 190: `super().__init__(...)`  
- Before line 191: `self.name = name`

**Correct order:**
```python
def __init__(self, name: str, ...):
    super().__init__(...)  # Line 190
    # INSERT HERE:
    if "." in name:
        raise ValueError("'name' may not contain a dot '.' character.")
    # END INSERTION
    self.name = name  # Line 191
```

**Why this order:**
1. `super().__init__()` must run first to initialize parent class
2. Validation runs immediately after before using the value
3. Prevents storing invalid state in `self.name`
4. Matches upstream PR #4045 exact placement

**Lines:** Insert between 190-191 at base commit d8c37f43724c

**Links:** [[flask-blueprint-validation-pattern]] [[flask-endpoint-validation-valueerror]]
