---
name: sphinxcontrib-stubs
description: Added stubs for sphinxcontrib extensions to avoid version requirement errors
metadata:
  type: feedback
---

Created minimal `setup(app)` functions in `sphinxcontrib/*/__init__.py` files for applehelp, devhelp, htmlhelp, qthelp, and serializinghtml. These no-op stubs prevent import errors due to version constraints in older Sphinx versions.

**Why:** The older Sphinx (1.8.1) cannot load the full sphinxcontrib extensions which require newer Sphinx, causing build failures.

**How to apply:** Include these stub files when using Sphinx 1.8.1 to satisfy import requirements without pulling in newer dependencies.
