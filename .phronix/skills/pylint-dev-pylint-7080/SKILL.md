---
name: pylint-dev-pylint-7080
description: Notes on pylint-dev/pylint-7080 (ignore-paths/--recursive bug): confirmed repro, refuted hypotheses, and cross-task approach/topic mismatches to ignore.
subject: pylint-dev-pylint-7080
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Reproduction commands for the issue's tree shape (does not reproduce on Linux) |
| `I2` | Instructions | Reproduction: absolute-path argument defeats anchored ignore-paths regex |
| `R1` | Rules | _discover_files and expand_modules ignore-paths checks are NOT redundant |
| `R2` | Rules | Windows backslash/forward-slash mismatch already handled in argument.py |
| `R3` | Rules | Passing ignore-paths recursive tests don't prove _discover_files filters |
| `R4` | Rules | Approaches referencing sympy unitsystem.py dimension logic are misassigned to this topic |
| `R5` | Rules | os.walk's leading './' prefix defeats anchored ignore-paths regexes too |
| `X1` | References | Test file name mismatch: unittest_expand_modules.py, not test_expand_modules.py |
| `X2` | References | Same leak class also hit sympy__sympy-21847 |


## Instructions

### I1 — Reproduction commands for the issue's tree shape (does not reproduce on Linux)

To recheck or extend the Linux repro attempt: `mkdir -p tmp/research/repro/src/gen && echo 'import os' > tmp/research/repro/src/region_selection.py && echo 'x=1' > tmp/research/repro/src/gen/about.py && cd tmp/research/repro && PYTHONPATH=<repo-root> python -m pylint --recursive=y --ignore-paths='^src/gen/.*$' src`. On Linux at commit 3c5eca2ded3d this correctly excludes src/gen/about.py (both with and without src/gen/__init__.py) — i.e. no repro at this simple 2-level depth. See refuted approach literal-issue-repro-two-level-tree-linux and root-cause aspects (aspect-discover-files-ignore-check, aspect-expand-modules-vs-discover-files-paths) for where the actual bug condition might live (deeper nesting, cwd-relative paths, or Windows path separators — none of which were tested here due to budget).

### I2 — Reproduction: absolute-path argument defeats anchored ignore-paths regex

To reproduce the actual bug, pass an ABSOLUTE path as the files_or_modules CLI argument: Run(['--ignore-paths=^src/gen/.*$', os.path.abspath('src')]) leaks src/gen/about.py through (confirmed via rated-score delta of -5.00 vs. the working relative-path run). This happens identically with or without --recursive=y, because expand_modules walks subdirectories itself via modutils.get_module_files whenever given a directory argument, independent of the --recursive flag. So this is NOT a _discover_files/expand_modules sequencing issue — it's that an absolute input path yields absolute file paths somewhere in get_python_path / modutils.modpath_from_file / path normalization, and the user's anchored (^-prefixed), relative-style regex can never match an absolute path. This is the most promising lead for the real fix; investigate path normalization / regex-anchoring, likely a separate aspect than expand_modules-vs-discover_files sequencing. Test scripts and synthetic trees left at tmp/research/test_expand*.py, testproj/, testproj2/, src/, src2/ in that worktree.

## Rules

### R1 — _discover_files and expand_modules ignore-paths checks are NOT redundant

With --recursive=y, PyLinter._discover_files() (pylinter.py:600-607) checks _is_ignored_file() against the directory ROOT being walked (e.g. "src/gen"), while expand_modules()'s own _is_ignored_file() call (expand_modules.py:78-81) checks the FULL FILE PATH (e.g. "src/gen/about.py"). A regex like ^src/gen/.*$ typically does not match the bare directory root but does match the full file path, so expand_modules's check is the one doing real, reachable exclusion work. Both use the same self.config.ignore_paths object (pylinter.py:1014, 604, 778) — they don't disagree on pattern lists either. Do not re-propose "expand_modules's check is unreachable/redundant" as the bug cause for pylint-7080; it was directly instrumented and refuted.

### R2 — Windows backslash/forward-slash mismatch already handled in argument.py

_regexp_paths_csv_transfomer in pylint/config/argument.py:110-121 already compiles ignore-paths regexes into a dual pattern accepting both backslash- and forward-slash-style paths (e.g. ^src/gen/.*$ becomes ^src\\\\gen\\\\.*$|^src/gen/.*$), present at base commit 3c5eca2d. Don't chase "Windows separator mismatch" as the cause of the ignore-paths bug — verified directly that the dual pattern matches both "src\\gen\\about.py" and "src/gen/about.py".

### R3 — Passing ignore-paths recursive tests don't prove _discover_files filters

tests/test_self.py's test_ignore_recursive/test_ignore_pattern_recursive/test_ignore_path_recursive pass, but not because _discover_files (pylinter.py:585-619) does per-file ignore-paths checks — it doesn't (no per-file check at pylinter.py:609-617). They pass because check() later calls expand_modules() on the full file list (pylinter.py:774), and expand_modules() applies _is_ignored_file per item (expand_modules.py:80-83) — that's the real save. Don't treat these tests as evidence _discover_files-level filtering works; write a test that exercises _discover_files directly (or with an anchored regex + deep non-package subdir) to actually cover that layer. unittest_expand_modules.py's test_expand_modules_with_ignore also only calls expand_modules() directly, never _discover_files/Run().

### R4 — Approaches referencing sympy unitsystem.py dimension logic are misassigned to this topic

Three tune/measurement assignments to pylint-dev__pylint-7080 (base commit 3c5eca2ded3d) named approaches that are actually about sympy: `raise-on-non-dimensionless-function-arg`, `simplify-dims-and-fix-multiarg-return-arity`, and `coerce-dimensionless-in-function-branch`, all targeting `sympy/physics/units/unitsystem.py`. That file does not exist in this pylint checkout.

**Why:** approach text leaks in from the sibling sympy__sympy-24066 task sharing the same machine — the mirror image of [[sympy-sympy-24066#R1]] (pylint text leaking into sympy) and [[pallets-flask-5063#R4]] (pylint text leaking into flask).

**How to apply:** do not search this checkout for unitsystem.py or dimension/exp() logic; flag the mismatch immediately and redirect to the real pylint ignore-paths work at [[pylint-dev-pylint-7080#I2]]. The actual sympy fix belongs at [[sympy-sympy-24066#X1]].

### R5 — os.walk's leading './' prefix defeats anchored ignore-paths regexes too

os.walk('.') yields root paths with a leading './' prefix (e.g. './src/gen', not 'src/gen'). An anchored user regex like ^src/gen/.*$ or even ^src/gen$ fails to match this prefixed form, so a directory-root check against os.walk's raw root string can silently miss even after the trailing-separator gap ([[pylint-discover-files-ignore-paths#R1]]) and the per-file-check gap (R1 above) are both fixed.

**Why:** found while diagnosing the same recursive ignore-paths bug family — a third, independent way the anchored-regex-vs-path-string mismatch shows up.

**How to apply:** any fix that checks os.walk's root against ignore_paths must strip a leading './' (or normalize via os.path.normpath) before matching, in addition to the trailing-separator and per-file fixes already recorded.

## References

### X1 — Test file name mismatch: unittest_expand_modules.py, not test_expand_modules.py

At base commit 3c5eca2ded3d, the expand_modules test file is named tests/lint/unittest_expand_modules.py (not tests/lint/test_expand_modules.py, despite that name appearing in the task brief and other aspect notes). tests/test_self.py's name is correct as-is. Anyone grepping for test_expand_modules.py and finding nothing should check unittest_expand_modules.py before concluding there's no coverage.

### X2 — Same leak class also hit sympy__sympy-21847

The cross-task approach-text leak described in [[pylint-dev-pylint-7080#R4]] recurred on a third topic: sympy__sympy-21847 got `rewrite_ignore_paths_patterns_to_be_root_relative` and `add_per_file_is_ignored_check_in_discover_files` handed to its tune/setup stages. See [[sympy-itermonomials#X3]] for that topic's record.
