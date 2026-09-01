# Lessons — pylint-recursive-ignore-paths-fix

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — What failed when attempting to fix --recursive=y ignoring ignore-paths

**2026-08-31** — What failed when attempting to fix --recursive=y ignoring ignore-paths

PROBLEM: The --recursive=y flag in pylint was ignoring ignore-paths configuration from pyproject.toml/rc files, causing files matching ignore patterns to still be checked during recursive mode.

ROOT CAUSE ANALYSIS: During investigation of the bug, the code flow was traced through:
1. `pylint/lint/expand_modules.py:_is_ignored_file` (line 49-60) - correctly checks element against ignore_list_paths_re
2. `pylint/lint/expand_modules.py:expand_modules` (line 76-79) - calls _is_ignored_file but may not have properly compiled ignore paths
3. `pylint/lint/pylinter.py:_discover_files` (line 585-619) - has _is_ignored_file call at line 600-607 with self.config.ignore_paths

The specific failure point was that the ignore-paths patterns from the active configuration file (e.g., `ignore-paths = ["^src/gen/.*$"]`) were not being properly compiled into regex patterns and applied during the recursive file collection phase. While the _is_ignored_file function and the ignore-paths config option (type regexp_paths_csv) existed, the patterns were not reaching the file discovery code path when --recursive=y was used.

WHAT WAS TRIED: Initial approach assumed the existing _is_ignored_file call in _discover_files would handle the patterns correctly, but testing confirmed that files matching ignore-paths patterns were still being checked during recursive mode. The patterns existed in self.config.ignore_paths but were not being compiled/applied in the recursive discovery flow.

TESTS THAT WOULD HAVE FAILED: Any test running `pylint --recursive=y <directory>` with `ignore-paths` configured in pyproject.toml that expects files matching those patterns to be excluded. Specifically, a test with `ignore-paths = ["^src/gen/.*$"]` and `pylint --recursive=y src/` would still report errors from src/gen/ files, confirming the bug.

LESSON: Configuration options must be verified end-to-end — having the option defined (regexp_paths_csv type) and the check function (_is_ignored_file) implemented is not sufficient. The patterns must be explicitly compiled and applied at every code path where file collection occurs, especially in recursive mode. Future fixes must trace the full flow from config parsing → pattern compilation → application at each usage point, not assume prior steps are working.
