---
name: pattern-construction-dual-branch-fix
description: Pattern construction bugs in conditional branches often require fixing all branches, not just the commonly-used one
metadata:
  type: feedback
---

**Context**: When fixing regex patterns that are constructed in conditional branches (if/else), verify that all branches require the same fix.

**Pattern identified in**: pylint fixme checker (`pylint/checkers/misc.py`, lines 119-128), where regex construction has two branches:
```python
if self.config.notes_rgx:
    regex_string = rf"#\s*({notes}|{self.config.notes_rgx})\b"  # Line 124
else:
    regex_string = rf"#\s*({notes})\b"  # Line 126
```

**Why both branches matter**: Even when the bug manifests primarily in one branch, both branches may have the same underlying issue:
- The `notes` branch (line 126) fails for punctuation-only note tags
- The `notes_rgx` branch (line 124) has the same `\b` suffix, which would break even a user-provided regex that matches punctuation

**How to apply**: When fixing pattern construction in conditional logic:
1. Identify all branches that construct similar patterns
2. Check if the fix applies to the pattern structure itself (not just the conditional content)
3. Apply the fix consistently to all branches that share the pattern structure
4. Don't assume one branch is "unused" or "edge case" without verification

**Why**: Incomplete fixes leave latent bugs that manifest when users exercise the unfixed branch. A half-fixed feature is worse than an obviously broken one because it appears to work in common cases.
