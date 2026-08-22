---
name: sitecustomize-src-sys-path
description: Add sitecustomize.py to repository root to insert src directory into sys.path for Flask test runs
metadata:
  type: project
---

The tests import the Flask package from the src directory. By default, Python does not include src in sys.path, causing ImportError. Adding a sitecustomize.py file at the repository root that appends the absolute path of src to sys.path resolves this.

```python
import os
import sys

# Add the src directory to sys.path
repo_root = os.path.abspath(os.path.dirname(__file__))
src_path = os.path.join(repo_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
```

Place this file at the repository root (same level as `setup.py`). This ensures that any test or script run from the repository can import the Flask package from `src/flask`.

**Why this works:** Python automatically imports `sitecustomize` if it is present on the import path. By placing it in the repo root (which is on the import path when running tests), the code runs before any other imports, fixing the path issue.
