---
name: pylint-missing-init-fix
description: Adding a/b.py resolves missing __init__ error in pylint when a/a.py exists
metadata:
  type: lesson
---

When pylint reports a missing __init__ error for package a, adding an empty module a/b.py resolves the error because it forces Python to treat a as a package. This works even when a/a.py is present.

**Why:** The presence of a submodule file signals to the import system that the directory is a package, satisfying pylint's package detection.

**How to apply:** If encountering "missing __init__" errors, create an empty file a/b.py (or any submodule) alongside existing modules.
