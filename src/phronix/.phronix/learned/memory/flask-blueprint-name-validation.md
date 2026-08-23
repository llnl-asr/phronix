---
name: flask-blueprint-name-validation
description: Superseded — see flask-blueprint-name-dot-validation-research for the complete (all-three-checks) fix.
metadata:
  type: reference
---

This memory only covered the blueprint-name check in isolation and did not mention the endpoint/view_func checks in `add_url_rule` also needing conversion from `assert` to `ValueError`. Superseded by [[flask-blueprint-name-dot-validation-research]], which records the complete, upstream-confirmed fix (all three checks, PR #4045). Kept for backlink continuity; treat the other memory as canonical.

[[flask-blueprint-name-dot-validation-research]]
