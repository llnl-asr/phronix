---
name: ignore-paths-config
description: Add `ignore-paths` entry to pyproject.toml to exclude generated `src/gen` files from pylint.
metadata:
  type: feedback
---

Directive: In any `pyproject.toml` for a test repo, set:
```toml
[tool.pylint.MASTER]
ignore-paths = ["^src/gen/.*$"]
```
Why: Prevents pylint from linting generated files, ensuring ignore‑list logic is exercised only on relevant source files.
