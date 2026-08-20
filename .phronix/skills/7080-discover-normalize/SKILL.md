---
name: 7080-discover-normalize
description: Research on 7080 discover normalize. Covers why does recursive mode bypass path normalization that non-recursive mode applies; where exactly should path normalization occur: in _discover_files, in _is_ignored_file, or before pattern matching; pR #7080 normalized paths in expand_modules but was later reverted or incomplete - does it apply to _discover_files path. Approaches tried: apply_pr_7080_pattern_to_discover, normalize_in_is_ignored_file, normalize_in_discover_files, normalize_in_expand_modules.
subject: 7080-discover-normalize
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to 7080 discover normalize |
| `X1` | References | Tried: apply_pr_7080_pattern_to_discover |
| `X2` | References | Tried: normalize_in_is_ignored_file |
| `X3` | References | Tried: normalize_in_discover_files |
| `X4` | References | Tried: normalize_in_expand_modules |
| `X5` | References | Tried: document_pattern_requirements |
| `X6` | References | Tried: normalize_both_locations |
| `X7` | References | Tried: backport_pr_7080_exact_fix |
| `X8` | References | Tried: normalize_subfilepath_at_line_145 |
| `X9` | References | Sources consulted for 7080 discover normalize |











## Instructions

### I1 — How to evaluate a change to 7080 discover normalize

Figure of merit: **ignore_paths_respected** (max, target 1.0).

Measured by: Run pylint --recursive=y on test directory with ignore-paths configured for a subdirectory. Score 1.0 if no files from ignored path appear in output, 0.0 otherwise. Command: create test structure, configure ignore-paths pattern, run pylint --recursive=y, check output does not contain files matching ignore pattern.

Cases differ along: directory_depth, ignore_pattern_form, path_form.

## Rules

## References

### X1 — Tried: apply_pr_7080_pattern_to_discover

Apply the same normalization pattern from PR #7080 to the _discover_files code path

**Hypothesis**: PR #7080 fixed expand_modules by normalizing paths there. The same fix should apply to _discover_files which is a parallel code path. Applying normalization consistently across both paths will fix the bug. Falsifiable by: verifying that recursive and non-recursive produce same filtering behavior.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: normalize_in_is_ignored_file

Add os.path.normpath(element) at the start of _is_ignored_file() function to normalize paths before pattern matching. This is a defensive programming fix that makes the function robust for all callers (both recursive and non-recursive modes).

**Hypothesis**: The bug is architectural: _is_ignored_file assumes normalized paths but doesn't enforce this. Both recursive and non-recursive modes pass unnormalized paths. Normalizing inside _is_ignored_file before pattern matching will fix both modes with one change. Falsifiable by: applying the fix and testing that pattern ^tests/.*$ matches both './tests' and 'tests'.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: normalize_in_discover_files

Normalize paths in _discover_files before passing to _is_ignored_file. REJECTED: Only fixes one entry point, expand_modules also calls _is_ignored_file and would remain broken. Not a complete solution.

**Hypothesis**: Normalizing in _discover_files before calling _is_ignored_file will fix recursive mode. Falsifiable by: recursive mode tests pass but non-recursive mode still fails with same pattern matching issue.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: normalize_in_expand_modules

Normalize paths in expand_modules before the _is_ignored_file call at line 78. REJECTED: Only fixes non-recursive entry point, recursive mode via _discover_files would remain broken. Not a complete solution.

**Hypothesis**: Normalizing in expand_modules before calling _is_ignored_file will fix non-recursive mode. Falsifiable by: non-recursive mode tests pass but recursive mode still fails.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: document_pattern_requirements

Document that ignore-paths patterns must account for ./ prefixes and path variations. REJECTED: Breaks existing user configurations, makes patterns overly complex, violates principle of least surprise. The tool should normalize, not the user.

**Hypothesis**: Changing pattern documentation to require users to account for ./ prefixes will resolve the mismatch. Falsifiable by: users complain that patterns like ^\.?/?\btests/.*$ are too complex and existing configs break.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: normalize_both_locations

Apply normalization in TWO locations: (1) inside _is_ignored_file at line 55, AND (2) at line 145 before _is_in_ignore_list_re call on subfilepath. The duplicate logic means fixing only the shared function is incomplete.

**Hypothesis**: PR #7080 normalized in _is_ignored_file which is shared by both modes. However there is duplicate pattern matching logic at expand_modules.py line 145 that bypasses _is_ignored_file. Complete fix requires normalizing in BOTH locations. Falsifiable by: tests pass after fixing _is_ignored_file but fail when subfilepath with ./ prefix is processed.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: backport_pr_7080_exact_fix

Add `element = os.path.normpath(element)` as the first line inside _is_ignored_file() function (expand_modules.py:55), exactly as done in upstream PR #7080 commit d060f77

**Hypothesis**: The bug is architectural: _is_ignored_file() receives unnormalized paths (with ./, //, etc) from multiple call sites but matches them against user patterns that assume normalized form. Normalizing inside the function before pattern matching fixes all callers with one change. Falsifiable by: the hidden test test_ignore_path_recursive_current_dir must pass, and recursive mode with "." as input must 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: normalize_subfilepath_at_line_145

In addition to PR #7080's fix inside _is_ignored_file, also normalize subfilepath before the duplicate check at line 145: `subfilepath = os.path.normpath(subfilepath)` before calling _is_in_ignore_list_re

**Hypothesis**: There are TWO places where ignore_list_paths_re patterns are checked: (1) inside _is_ignored_file at line 59, and (2) directly at line 145 bypassing _is_ignored_file. If modutils.get_module_files returns unnormalized paths, line 145's subfilepath might also need normalization. Falsifiable by: checking if test fails when ignore pattern should match a subfilepath from get_module_files, or passes whe

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Sources consulted for 7080 discover normalize

- GitHub PR #7080 (https://github.com/pylint-dev/pylint/pull/7080), commit d060f7726b77e82f64f5b550c51ba0405ff0d42f. Investigation traced why recursive mode fails: os.walk() preserves ./ prefixes, _is_i
- Investigation of pylint/lint/expand_modules.py lines 78 vs 143-145 showing duplicate pattern matching logic. PR #7080 analysis from GitHub.
- PR #7080 at https://github.com/pylint-dev/pylint/pull/7080/files and commit d060f77
- Upstream PR #7080 merged June 28 2022 at https://github.com/pylint-dev/pylint/pull/7080/files, commit d060f7726b77e82f64f5b550c51ba0405ff0d42f. This exact 1-line fix was verified by maintainers and ba
