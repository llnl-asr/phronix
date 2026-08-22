---
name: verify-fix-absence
description: Verify fix is actually missing before applying backport or known solution
metadata:
  type: feedback
---

**What to Check**: When backporting or applying a known fix, verify the fix is actually missing in your version.

**How**: 
1. Identify the specific code change from the PR/commit
2. Look at the exact file and line number in your working version
3. Confirm the change is absent (not just different)

**Why This Matters**: 
- PR may have already been cherry-picked to your branch
- Fix may exist in a different form (refactored)
- Version tags can be misleading about what commits are included

**Detection Methods**:
- `git log --all --format="%H %s" | grep "<PR title>"`
- Direct code inspection at the target location
- Check for the exact line that should have been added

**Example**: pylint PR #7080 targeted v2.14.4, working version was v2.14.3-213-g64e918f8. Git log showed no matching commit, code inspection confirmed `element = os.path.normpath(element)` was missing from `_is_ignored_file`.

**Anti-Pattern**: Assuming the fix is missing based only on version number without checking the code.

**Related**: [[pylint-pr-7080-fix]]
