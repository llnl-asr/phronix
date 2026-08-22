---
name: duplicate-pattern-matching-pitfall
description: Pattern matching logic duplication requires fixing all locations, not just shared utility
metadata:
  type: lesson
---

**Symptom**: Path normalization fix applied in shared utility function but bug still manifests in some cases.

**Root Cause**: Pattern matching logic duplicated in multiple locations - some use shared utility function, others inline the same logic. Fixing the utility function doesn't fix the inline duplicates.

**Detection Signal**:
- Look for direct calls to lower-level matching functions (like `_is_in_ignore_list_re`)
- Look for similar pattern matching logic that appears in multiple locations
- Check if all pattern matching goes through the shared function or bypasses it

**Example**: In pylint expand_modules.py:
- Line 78: calls `_is_ignored_file()` (shared utility)
- Lines 143-145: directly calls `_is_in_ignore_list_re()` (inlines the logic)
- Fixing `_is_ignored_file` doesn't fix line 145

**Solution**: Either:
1. Apply normalization fix to ALL locations (shared + inline duplicates)
2. Refactor inline duplicates to use shared utility function (better long-term)

**Why This Matters**: A "complete" fix that misses inline duplicates appears to work initially but fails in edge cases when the duplicated code path is exercised.

**Related**: [[defensive-path-normalization]]
