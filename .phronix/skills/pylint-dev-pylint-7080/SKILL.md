---
name: pylint-dev-pylint-7080
description: Research on pylint dev pylint 7080. Covers does _discover_files (pylinter.py) fail to normalize os.walk's root/file paths (e.g. leading './' from os.walk('.'), or '..'-relative paths) before matching them against ignore_paths/ignore_patterns regexes, causing anchored regexes like '^ignored_subdirectory/.*$' to never match; is the pre-existing per-root-directory ignore check (lines 600-607, present before any attempt's edit) already failing for this exact test scenario, independent of attempt-1's added per-file check — i.e. is the bug upstream of where attempt-1 patched; does the 'any(root.star
subject: pylint-dev-pylint-7080
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to pylint dev pylint 7080 |
| `X1` | References | Where research on this subject stands |













## Instructions

### I1 — How to evaluate a change to pylint dev pylint 7080

Figure of merit: **ignore_paths_recursive_pass_rate** (max, target 1.0).

Measured by: Fraction of corpus instances where `python -m pylint --recursive=y <target>` run from the repo's own checkout (never a globally installed pylint), against a temp directory tree with a pyproject.toml/pylintrc declaring ignore-paths/ignore/ignore-patterns, produces ZERO messages and exit code 0 for files under the ignored path/subtree, while files outside it are still linted normally (non-empty outp

Cases differ along: config_source, expect_ignored, ignore_option, ignored_entity, target_arg_form.

## Rules

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **ignore_paths_recursive_pass_rate** (max, target 1.0).

**Still open**
- aspect not yet answered: path_normalization_in_discover_files
- aspect not yet answered: skip_subtrees_prefix_matching_bug
- aspect not yet answered: upstream_fix_shape

**Ruled out**
- pylint/lint/pylinter.py (failed ignore_paths_recursive_pass_rate=1.0) — try 2: tried against the target tests, 0 passing

**Where the detail is**
- pylint/lint/pylinter.py: benchmark attempt
- full record: research topic `pylint-dev__pylint-7080` (via research_status, only if this summary is not enough)