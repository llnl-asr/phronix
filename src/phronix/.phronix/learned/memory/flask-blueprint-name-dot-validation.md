---
name: flask-blueprint-name-dot-validation
description: Superseded — see flask-blueprint-name-dot-validation-research for the complete fix; kept for the DeprecationWarning test-suite note.
metadata:
  type: reference
---

The dot-validation fix itself is superseded by [[flask-blueprint-name-dot-validation-research]] (complete, upstream-confirmed, all three checks) — treat that memory as canonical.

Distinct fact kept here: the test suite can be blocked by a DeprecationWarning config that treats warnings as errors, resolvable by adjusting `filterwarnings` in setup.cfg. Unrelated to the dot-validation logic itself, noted here since it was found in the same investigation.
