---
name: test-ignore-path-recursive-current-dir
description: Test case that validates pylint --recursive=y with current directory as input
metadata:
  type: reference
---

**Test**: `tests/test_self.py::TestRunTC::test_ignore_path_recursive_current_dir`

**What it validates**: When running `pylint --recursive=y` with `"."` as the target directory, files matching `ignore-paths` patterns must be excluded from output.

**Why this test matters**: Running pylint on `"."` causes `os.walk()` to yield paths with `"./\"` prefix (e.g., `"./ignored_subdirectory/failing.py"`). Regex patterns like `^ignored_subdirectory/.*$` fail to match these prefixed paths unless normalization removes the prefix first.

**Expected behavior**: Exit code 0 (no violations found, because violating files are in ignored paths).

**Actual failure when normalization missing**: Exit code 20, with violations reported from files under `ignored_subdirectory/`, proving those files were not filtered despite matching the ignore pattern.

**Related**: This test was added as part of PR #7080 to prevent regression of the ignore-paths normalization fix.
