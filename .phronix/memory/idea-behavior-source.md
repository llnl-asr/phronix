---
name: idea-behavior-source
description: Location of Blueprint name validation in Flask source
metadata:
  type: reference
---

The Blueprint name validation that raises a ValueError for names containing a dot is performed in the ``Blueprint`` class ``__init__`` method, located in ``flask/blueprints.py``.
Specifically, lines around 191‑194 contain:
```python
self.name = name
if "." in name:
    raise ValueError("Blueprint name must not contain a dot: %r" % name)
```
This check ensures blueprint names do not include a period, raising the error when such a name is passed to ``Blueprint``.

**Why:** Identifies the exact source responsible for rejecting dot‑containing blueprint names, answering the question about where validation occurs.

**How to apply:** When debugging blueprint registration errors, inspect ``flask/blueprints.py`` at the ``Blueprint.__init__`` implementation for this validation logic.
