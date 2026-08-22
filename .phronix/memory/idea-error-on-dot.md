---
name: idea-error-on-dot
description: Blueprint name with dot error
metadata:
  type: project
---

**Why:** Blueprint names containing a dot are invalid per Flask design and raise a ValueError on registration.
**How to apply:** Validate blueprint name before creating; raise custom error or sanitize name.
