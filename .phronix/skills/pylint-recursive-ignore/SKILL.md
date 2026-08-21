---
name: pylint-recursive-ignore
description: Where recursive-mode ignore/ignore-patterns/ignore-paths tests and fixtures live in the pylint repo
subject: pylint-recursive-ignore
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Basic ignore-paths regex against a subdirectory works fine at base commit |
| `R1` | Rules | Recursive discovery has two separate ignore-check implementations |
| `R2` | Rules | __init__.py short-circuits skip_subtree marking in _discover_files |
| `X1` | References | Existing recursive+ignore test locations |





## Instructions

### I1 — Basic ignore-paths regex against a subdirectory works fine at base commit

Manually verified (outside existing fixtures, under /tmp/repro<node>/{good.py,sub/bad.py}) that both anchored (`^/tmp/repro<node>/sub/.*`) and unanchored (`.*/sub$`) --ignore-paths patterns correctly cause --recursive=y to skip the subdirectory (exit 0), and without --ignore-paths the fixture is correctly scanned (exit 4, bad.py flagged). Also confirmed config.ignore/.ignore_patterns/.ignore_paths correctly reflect CLI values despite dest=black_list/black_list_re aliasing in base_options.py — not a source of divergence.

Do not re-investigate these two mechanisms (plain regex matching against subdir path, and the black_list dest aliasing) as candidate root causes for pylint-7080 — both were checked directly and work correctly. The real bug is more specific than plain directory-level ignore-paths matching.

## Rules

### R1 — Recursive discovery has two separate ignore-check implementations

PyLinter._discover_files (pylint/lint/pylinter.py lines ~585-619) is a DIFFERENT code path from expand_modules() (pylint/lint/expand_modules.py). _discover_files only runs when config.recursive is true; it does its own os.walk + its own _is_ignored_file(root, ignore, ignore_patterns, ignore_paths) check per directory (lines ~600-607), skipping subtrees whose root matches. It duplicates ignore logic separately from expand_modules(), which is exercised by tests/lint/unittest_expand_modules.py but only in non-recursive mode.

Why it matters: a fix or bug affecting recursive-mode ignore-paths may need to be diagnosed in _discover_files specifically, not in expand_modules, and the two could diverge (e.g. absolute vs relative path formatting) since they're not sharing one implementation.

How to apply: when investigating recursive+ignore bugs, check both functions and don't assume expand_modules() tests give coverage for recursive mode.

### R2 — __init__.py short-circuits skip_subtree marking in _discover_files

In PyLinter._discover_files (pylint/lint/pylinter.py lines ~609-611), once a walked directory contains __init__.py in its files, it's short-circuited to `yield root` and marked as a skip_subtree boundary. This happens in the same pass as the ignore check on that root. Unverified but plausible: a package (dir with __init__.py) nested inside an otherwise-ignored subtree might not be excluded correctly, because none of the existing fixtures (tests/regrtest_data/directory/ignored_subdirectory/) combine "ignored" with "contains __init__.py" — ignored_subdirectory is flat, only has failing.py.

How to apply: if reproducing pylint-7080 or similar recursive-ignore bugs, try a fixture where the ignored subtree contains a package (__init__.py), not just loose .py files — existing fixtures/tests don't cover that combination.

## References

### X1 — Existing recursive+ignore test locations

tests/test_self.py class TestRunTC lines ~1231-1345 has the recursive-ignore test suite: test_regression_recursive, test_recursive, test_ignore_recursive, test_ignore_pattern_recursive, test_ignore_path_recursive, test_recursive_current_dir, test_regression_recursive_current_dir. All 7 PASS on base commit 64e918f8 (pylint-7080).

Fixtures: tests/regrtest_data/directory/ — has ignored_subdirectory/failing.py (flat, no __init__.py), package/__init__.py + package/module.py + package/subpackage/, subdirectory/module.py + subsubdirectory/module.py.

tests/lint/unittest_expand_modules.py lines 119-153 covers --ignore-paths via expand_modules()/_is_in_ignore_list_re directly, but WITHOUT --recursive — no recursive-mode coverage there.

tests/lint/test_pylinter.py has no recursive- or ignore-related tests at all.
