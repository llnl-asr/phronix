---
name: module-name-conflict-resolution-prioritization
description: Record that module-name conflict resolution currently prioritizes package over .py file
metadata:
  type: project
---

When resolving module name conflicts, the system incorrectly gives precedence to a package directory over a .py file of the same name. This can cause import errors where the intended module is a single file.

**Why:** The resolution algorithm checks for a package first, which shadows a similarly named .py file.

**How to apply:** Adjust the conflict resolution order to check for a .py file before a package when both exist at the same path level.

**Reference:** [[phronix-learning-reconcile]]
