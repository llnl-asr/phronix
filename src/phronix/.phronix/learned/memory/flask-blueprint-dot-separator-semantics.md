---
name: flask-blueprint-dot-separator-semantics
description: Flask blueprint naming: dot character is structural separator in blueprint.endpoint notation, not allowed in blueprint names
metadata:
  type: reference
---

**Why dots are forbidden in Flask blueprint names**

The dot character (`.`) has semantic meaning in Flask's blueprint and endpoint naming system. It serves as the **structural separator** between blueprint names and endpoint names.

**How dots are used as separators:**

1. **Endpoint construction** (src/flask/blueprints.py line 101):
   ```python
   f"{self.name_prefix}{self.blueprint.name}.{endpoint}"
   ```
   Creates endpoints like `blueprint_name.endpoint_name`

2. **Nested blueprint keys** (lines 297, 302):
   ```python
   key = self.name if key is None else f"{self.name}.{key}"
   ```
   Creates hierarchical keys like `parent.child.grandchild`

3. **Endpoint parsing** (src/flask/wrappers.py lines 75-76):
   ```python
   if self.url_rule and "." in self.url_rule.endpoint:
       return self.url_rule.endpoint.rsplit(".", 1)[0]
   ```
   Extracts blueprint name by splitting on the rightmost dot

**Why this matters:**

A blueprint named `"foo.bar"` registered with endpoint `"baz"` would create endpoint `"foo.bar.baz"`, which is indistinguishable from:
- Blueprint `"foo"` with sub-blueprint `"bar"` and endpoint `"baz"`

This creates ambiguity in the naming hierarchy that cannot be resolved.

**Source:** Issue #4041, PR #4045
**Related:** [[flask-blueprint-name-dot-validation-research]]
