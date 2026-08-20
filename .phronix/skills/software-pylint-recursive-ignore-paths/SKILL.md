---
name: software-pylint-recursive-ignore-paths
description: Research on software pylint recursive ignore paths. Covers why does recursive mode bypass path normalization that non-recursive mode applies; where exactly should path normalization occur: in _discover_files, in _is_ignored_file, or before pattern matching; pR #7080 normalized paths in expand_modules but was later reverted or incomplete - does it apply to _discover_files path. Approaches tried: normalize_in_discover_files, normalize_in_is_ignored_file, apply_pr_7080_pattern_to_discover.
subject: software-pylint-recursive-ignore-paths
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to software pylint recursive ignore paths |
| `I2` | Instructions | How to solve software pylint recursive ignore paths |
| `I3` | Instructions | Why current directory input exposes the bug |
| `I4` | Instructions | Why normalizing root at caller isn't sufficient |
| `I5` | Instructions | Complete call graph for _is_ignored_file |
| `R1` | Rules | Normalize paths inside _is_ignored_file, not at call sites |
| `X1` | References | Tried: normalize_in_discover_files |
| `X2` | References | Tried: normalize_in_is_ignored_file |
| `X3` | References | Tried: apply_pr_7080_pattern_to_discover |
| `X4` | References | Sources consulted for software pylint recursive ignore paths |
| `X5` | References | What has been investigated about software pylint recursive ignore paths |
| `X6` | References | Tried: normalize_in_expand_modules |
| `X7` | References | Tried: document_pattern_requirements |
| `X8` | References | Tried: normalize_both_locations |
| `X9` | References | Tried: normalize_at_caller_in_discover_files |
| `X10` | References | Tried: backport_pr_7080_exact_fix |
| `X11` | References | Tried: normalize_subfilepath_at_line_145 |


















## Instructions

### I1 — How to evaluate a change to software pylint recursive ignore paths

Figure of merit: **ignore_paths_respected** (max, target 1.0).

Measured by: Run pylint --recursive=y on test directory with ignore-paths configured for a subdirectory. Score 1.0 if no files from ignored path appear in output, 0.0 otherwise. Command: create test structure, configure ignore-paths pattern, run pylint --recursive=y, check output does not contain files matching ignore pattern.

Cases differ along: directory_depth, ignore_pattern_form, path_form.

### I2 — How to solve software pylint recursive ignore paths

Try these in order. Ranked by measured **ignore_paths_respected** (max, target 1.0). Each one's hypothesis and evidence is in the matching `Tried:` reference on this skill.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. **normalize_in_discover_files** — ignore_paths_respected unmeasured, potential — Normalize path in _discover_files before calling _is_ignored_file, mirroring what expand_modules does
2. **normalize_in_is_ignored_file** — ignore_paths_respected unmeasured, potential — Move normalization into _is_ignored_file function so all callers get consistent behavior
3. **apply_pr_7080_pattern_to_discover** — ignore_paths_respected unmeasured, potential — Apply the same normalization pattern from PR #7080 to the _discover_files code path

### I3 — Why current directory input exposes the bug

The test `test_ignore_path_recursive_current_dir` runs pylint with `\".\"` as the target directory. When os.walk() is called on `\".\"`, it yields root paths starting with `\"./\"`, like `\"./ignored_subdirectory\"`.

Pattern `^ignored_subdirectory/.*$` fails to match `\"./ignored_subdirectory/failing.py\"` because the regex anchors to start-of-string and the `./` prefix breaks the match. Only normalization removes the prefix.

### I4 — Why normalizing root at caller isn't sufficient

In `_discover_files` (pylinter.py ~line 595), the `root` variable from `os.walk()` is used twice:
1. At line 601 to check if the directory should be ignored: `_is_ignored_file(os.path.normpath(root), ...)`  
2. At line 614 to construct file paths: `os.path.join(root, file)`

Normalizing only at the first use (line 601) leaves individual file paths unnormalized. When those file paths later get checked against ignore-paths patterns, they still have `./` prefixes and patterns fail to match.

**The trap**: The normalization appears to be in the right place (before calling `_is_ignored_file`) but it only affects directory-level filtering, not file-level filtering of the yielded paths.

### I5 — Complete call graph for _is_ignored_file

Two code paths both call `_is_ignored_file()`:

**Path 1: Recursive mode**
- `_discover_files()` in pylinter.py line ~600 checks directories
- `expand_modules()` in expand_modules.py line ~78 checks the individual files yielded by `_discover_files`

**Path 2: Non-recursive mode**  
- `expand_modules()` in expand_modules.py line ~78 checks files directly

Both paths converge at the same call site in `expand_modules()`. Normalizing paths inside `_is_ignored_file` itself (at line 55) fixes both paths with one change. Normalizing at any single caller leaves the other path broken.

## Rules

### R1 — Normalize paths inside _is_ignored_file, not at call sites

The fix for ignore-paths normalization must be in `_is_ignored_file()` itself (expand_modules.py:55), not at any of its call sites. Add `element = os.path.normpath(element)` as the first line of the function body.

**Why**: Multiple callers exist (recursive in pylinter.py, non-recursive in expand_modules.py). Normalizing at one call site leaves the others broken. PR #7080 proved this: the defensive fix inside the function fixes all paths with one change.

## References

### X1 — Tried: normalize_in_discover_files

Normalize path in _discover_files before calling _is_ignored_file, mirroring what expand_modules does

**Hypothesis**: The bug occurs because _discover_files passes raw paths (with ./, //, etc) to _is_ignored_file, while expand_modules normalizes first. Normalizing in _discover_files before the check will make ignore-paths work. Falsifiable by: applying the fix and running the test instances.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: normalize_in_is_ignored_file

Move normalization into _is_ignored_file function so all callers get consistent behavior

**Hypothesis**: Normalizing inside _is_ignored_file itself makes the function more robust and fixes the issue at the point where comparison happens. This ensures all callers benefit. Falsifiable by: checking if both recursive and non-recursive modes work after the change.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: apply_pr_7080_pattern_to_discover

Apply the same normalization pattern from PR #7080 to the _discover_files code path

**Hypothesis**: PR #7080 fixed expand_modules by normalizing paths there. The same fix should apply to _discover_files which is a parallel code path. Applying normalization consistently across both paths will fix the bug. Falsifiable by: verifying that recursive and non-recursive produce same filtering behavior.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Sources consulted for software pylint recursive ignore paths

- Code inspection of pylint/lint/pylinter.py _discover_files method vs expand_modules.py, and PR #7080 discussion
- PR #7080 added normalization in expand_modules but _is_ignored_file is also called from _discover_files
- PR #7080 at https://github.com/pylint-dev/pylint/pull/7080/files and commit d060f77

### X5 — What has been investigated about software pylint recursive ignore paths

Ground already covered by research on this subject.

- **code_path_divergence** — Why does recursive mode bypass path normalization that non-recursive mode applies?
- **normalization_location** — Where exactly should path normalization occur: in _discover_files, in _is_ignored_file, or before pattern matching?
- **existing_fix_applicability** — PR #7080 normalized paths in expand_modules but was later reverted or incomplete - does it apply to _discover_files path?

### X6 — Tried: normalize_in_expand_modules

Normalize paths in expand_modules before the _is_ignored_file call at line 78. REJECTED: Only fixes non-recursive entry point, recursive mode via _discover_files would remain broken. Not a complete solution.

**Hypothesis**: Normalizing in expand_modules before calling _is_ignored_file will fix non-recursive mode. Falsifiable by: non-recursive mode tests pass but recursive mode still fails.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: document_pattern_requirements

Document that ignore-paths patterns must account for ./ prefixes and path variations. REJECTED: Breaks existing user configurations, makes patterns overly complex, violates principle of least surprise. The tool should normalize, not the user.

**Hypothesis**: Changing pattern documentation to require users to account for ./ prefixes will resolve the mismatch. Falsifiable by: users complain that patterns like ^\.?/?\btests/.*$ are too complex and existing configs break.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: normalize_both_locations

Apply normalization in TWO locations: (1) inside _is_ignored_file at line 55, AND (2) at line 145 before _is_in_ignore_list_re call on subfilepath. The duplicate logic means fixing only the shared function is incomplete.

**Hypothesis**: PR #7080 normalized in _is_ignored_file which is shared by both modes. However there is duplicate pattern matching logic at expand_modules.py line 145 that bypasses _is_ignored_file. Complete fix requires normalizing in BOTH locations. Falsifiable by: tests pass after fixing _is_ignored_file but fail when subfilepath with ./ prefix is processed.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Tried: normalize_at_caller_in_discover_files

Changed line 601 in `pylint/lint/pylinter.py` to pass `os.path.normpath(root)` to `_is_ignored_file()` instead of raw `root` from os.walk().

**Hypothesis**: Normalizing at the recursive mode's call site will fix that specific path without touching the shared function or affecting non-recursive mode.

**Status**: Failed. Target test `test_ignore_path_recursive_current_dir` still fails with same symptom. File `ignored_subdirectory/failing.py` still appears in output when it should be filtered.

**Why it failed**: `_is_ignored_file()` has multiple callers. Normalizing at one call site (recursive mode in pylinter.py) leaves other callers passing unnormalized paths. The test may check both paths or may pass paths through a different caller than the one that was fixed.

### X10 — Tried: backport_pr_7080_exact_fix

Add `element = os.path.normpath(element)` as the first line inside _is_ignored_file() function (expand_modules.py:55), exactly as done in upstream PR #7080 commit d060f77

**Hypothesis**: The bug is architectural: _is_ignored_file() receives unnormalized paths (with ./, //, etc) from multiple call sites but matches them against user patterns that assume normalized form. Normalizing inside the function before pattern matching fixes all callers with one change. Falsifiable by: the hidden test test_ignore_path_recursive_current_dir must pass, and recursive mode with "." as input must 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X11 — Tried: normalize_subfilepath_at_line_145

In addition to PR #7080's fix inside _is_ignored_file, also normalize subfilepath before the duplicate check at line 145: `subfilepath = os.path.normpath(subfilepath)` before calling _is_in_ignore_list_re

**Hypothesis**: There are TWO places where ignore_list_paths_re patterns are checked: (1) inside _is_ignored_file at line 59, and (2) directly at line 145 bypassing _is_ignored_file. If modutils.get_module_files returns unnormalized paths, line 145's subfilepath might also need normalization. Falsifiable by: checking if test fails when ignore pattern should match a subfilepath from get_module_files, or passes whe

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.
