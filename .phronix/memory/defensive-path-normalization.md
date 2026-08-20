---
name: defensive-path-normalization
description: Path comparison functions must normalize internally, not rely on callers
metadata:
  type: lesson
---

**Symptom**: Regex patterns fail to match paths with ./ prefixes or // separators even when semantically equivalent.

**Root Cause**: Functions that match user-provided regex patterns against filesystem paths assume normalized input but don't enforce this assumption. When multiple callers exist, some normalize and some don't, creating inconsistent behavior.

**Exact Fix**: Add path normalization (os.path.normpath) at the START of any function that performs pattern matching against paths, BEFORE the comparison. This makes the function defensive against all callers.

**Why This Location**:
- Single choke-point: fixes all callers with one change
- Defensive programming: function enforces its own preconditions
- Future-proof: new callers automatically get correct behavior
- Minimal: one line addition

**Anti-Pattern to Avoid**: Normalizing at call sites requires every current and future caller to remember to normalize. This is fragile and leads to bugs when code paths diverge.

**Evidence**: pylint issue #7080 - both recursive and non-recursive modes called _is_ignored_file but only one normalized paths before calling. PR #7080 fixed by normalizing inside the shared function.

**Related**: [[config-option-normalization-pattern]]
