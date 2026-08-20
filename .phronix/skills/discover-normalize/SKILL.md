---
name: discover-normalize
description: Research on discover normalize. Covers why does recursive mode bypass path normalization that non-recursive mode applies; where exactly should path normalization occur: in _discover_files, in _is_ignored_file, or before pattern matching; pR #7080 normalized paths in expand_modules but was later reverted or incomplete - does it apply to _discover_files path. Approaches tried: normalize_in_discover_files, normalize_in_is_ignored_file, apply_pr_7080_pattern_to_discover.
subject: discover-normalize
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to discover normalize |
| `X1` | References | Tried: normalize_in_discover_files |
| `X2` | References | Tried: normalize_in_is_ignored_file |
| `X3` | References | Tried: apply_pr_7080_pattern_to_discover |
| `X4` | References | Sources consulted for discover normalize |






## Instructions

### I1 — How to evaluate a change to discover normalize

Figure of merit: **ignore_paths_respected** (max, target 1.0).

Measured by: Run pylint --recursive=y on test directory with ignore-paths configured for a subdirectory. Score 1.0 if no files from ignored path appear in output, 0.0 otherwise. Command: create test structure, configure ignore-paths pattern, run pylint --recursive=y, check output does not contain files matching ignore pattern.

Cases differ along: directory_depth, ignore_pattern_form, path_form.

## Rules

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

### X4 — Sources consulted for discover normalize

- Code inspection of pylint/lint/pylinter.py _discover_files method vs expand_modules.py, and PR #7080 discussion
- PR #7080 added normalization in expand_modules but _is_ignored_file is also called from _discover_files
- PR #7080 at https://github.com/pylint-dev/pylint/pull/7080/files and commit d060f77
