---
name: module-name-conflict-resolution
description: rule: package modules take precedence over .py files
metadata:
  type: reference
---

When resolving module names, prioritize packages (directories with __init__.py) over similarly named .py files. **Why:** ensures correct package semantics and avoids accidental shadowing. **How to apply:** In import resolution, check for package directory first. [[module-name-conflict-resolution]]
