---
name: config-option-normalization-pattern
description: Pattern matching divergence across modes often due to inconsistent normalization
metadata:
  type: feedback
---

**Pattern**: User provides configuration with path patterns, tool has multiple code paths (modes/features) for file discovery, patterns work in some modes but not others.

**What to Check**:
1. Identify all file discovery entry points (recursive vs non-recursive, different APIs)
2. Trace each path to where pattern matching occurs
3. Check if path normalization happens consistently BEFORE pattern matching
4. Look for shared utility functions that multiple paths call

**Common Root Cause**: 
- Pattern matching function assumes normalized paths but doesn't enforce it
- Some callers normalize before calling, others don't
- The divergence is usually accidental, not intentional design

**Detection Signal**: 
- Same pattern works with some input forms but not others
- Works with explicit paths but fails with relative paths containing `./`
- Works in one mode but fails in another mode

**Investigation Strategy**:
1. Don't assume intentional divergence - look for shared code first
2. Check if fix location should be in shared utility vs each call site
3. Look for existing normalization elsewhere as evidence of intent

**Example**: pylint --recursive=y vs --recursive=n, both call _is_ignored_file but with different path forms.

**Related**: [[defensive-path-normalization]], [[os-walk-path-prefix-preservation]]
