---
name: pylint-pr-7080-fix
description: PR #7080 fixed pylint ignore-paths with --recursive by normalizing in _is_ignored_file
metadata:
  type: reference
---

**Issue**: pylint-dev/pylint#6964, fixed by PR #7080
**PR URL**: https://github.com/pylint-dev/pylint/pull/7080
**Merged**: June 28, 2022
**Target Release**: 2.14.4
**Commit**: d060f7726b77e82f64f5b550c51ba0405ff0d42f

**What It Fixed**: When using `pylint --recursive=y`, the `ignore-paths` configuration was ignored because paths from `os.walk()` contained `./` prefixes that didn't match user patterns.

**The Fix**: Added `element = os.path.normpath(element)` at the start of `_is_ignored_file()` function in `pylint/lint/expand_modules.py` (line 55).

**Why Single Location Works**: Both recursive (`_discover_files`) and non-recursive (`expand_modules`) modes call the same shared `_is_ignored_file()` function, so fixing it once fixes both paths.

**Applicability**: This fix is directly applicable to any version between v2.14.3 and v2.14.4 that doesn't have the PR merged. Check by looking for normpath call at start of `_is_ignored_file`.

**Test Coverage**: PR included `test_ignore_path_recursive_current_dir` that validates recursive mode with `"."` as target.

**Related**: [[defensive-path-normalization]], [[duplicate-pattern-matching-pitfall]]
