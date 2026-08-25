---
name: idea-module-search-order
description: Search order for module files vs package directories to avoid false missing __init__ errors
metadata:
  type: project
---

**Finding:**\nWhen pylint resolves a module name, it builds `additional_search_path` as `[".", module_path] + path`. This order makes the resolver check the current directory before the directory containing the target module, causing a false missing `__init__.py` error when a module file (e.g., `a/a.py`) exists without a package init.\n\n**Proposed fix:** Change construction to prioritize the module's directory: `additional_search_path = [module_path, "."] + path`. This aligns with Python's import precedence, allowing pylint to find the module file first and only fall back to package resolution if needed.\n\n**Impact & next steps:**\n- Verify no regression for legitimate packages with `__init__.py`.\n- Add tests for cases: module file without init, proper package, both present.\n- Update `pylint/lint/expand_modules.py` accordingly and run test suite.\n\n**Why recorded:** Captures the insight for future developers and tooling, ensuring the import order issue is addressed consistently.
