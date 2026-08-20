---
name: pylint-ignore-paths-normalization
description: Pylint ignore-paths fails when paths not normalized before regex matching
metadata:
  type: lesson
---

**Symptom:** `pylint --recursive=y` ignores the `ignore-paths` configuration and lints files that should be skipped.

**Root Cause:** Path normalization inconsistency between two file discovery code paths:
- Non-recursive mode (expand_modules) normalizes paths
- Recursive mode (_discover_files) passes raw paths with `./`, `//`, etc.
- Both call _is_ignored_file() but get different path forms
- Regex patterns like `^src/gen/.*$` fail to match `./src/gen/file.py`

**Exact Fix:** Add `element = os.path.normpath(element)` as the first line in `_is_ignored_file()` function in `pylint/lint/expand_modules.py`.

**Why:** Normalizing at the comparison point makes the function defensive and fixes both code paths with one change.

**Reference:** PR #7080 (https://github.com/pylint-dev/pylint/pull/7080) applied this exact fix and was merged upstream.

**Verification:** Must test both --recursive=y and non-recursive modes to ensure no regression in either path.
