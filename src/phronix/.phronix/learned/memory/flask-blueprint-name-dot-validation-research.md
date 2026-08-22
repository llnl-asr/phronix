---
name: flask-blueprint-name-dot-validation-research
description: Flask blueprint name validation: dots forbidden due to nested blueprint notation ambiguity (issue #4041, PR #4045)
metadata:
  type: reference
---

## Context
Flask 2.0 introduced nested blueprints which use dots as hierarchical separators (e.g., "parent.child.endpoint"). Blueprint names containing dots create ambiguity.

## Solution Pattern
**Location**: Blueprint.__init__ method in src/flask/blueprints.py
**Exception**: ValueError (not AssertionError)
**Check**: Simple `"." in name` string operator
**Message format**: "'name' may not contain a dot '.' character."

## Key Implementation Details
1. Validation occurs in __init__ for fail-fast behavior
2. Also update existing endpoint and view_func validation from assert to ValueError for consistency
3. This is a breaking change - tests using dotted blueprint names (like test_dotted_names) will fail

## Upstream Reference
- Issue: https://github.com/pallets/flask/issues/4041
- PR: https://github.com/pallets/flask/pull/4045
- Merged: May 13, 2021 into 2.0.x branch

## Why Not AssertionError
Flask changed from assert to ValueError in PR #4045 for all blueprint validation. ValueError is more appropriate for user input validation.

## Related Patterns
Nested blueprint name_prefix construction: `bp_options["name_prefix"] = options.get("name_prefix", "") + self.name + "."`
