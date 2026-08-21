---
name: normalize-ignore-paths
description: Research on normalize ignore paths. Covers how does pylint implement recursive directory traversal and where does it collect files; where and when are ignore-paths patterns applied during file collection; how does pylint load and merge configuration from different sources (pyproject.toml, pylintrc, setup.cfg). Approaches tried: normalize paths before ignore check, normalize subfilepath in recursive loop, normalize in is ignored file helper.
subject: normalize-ignore-paths
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to normalize ignore paths |
| `I2` | Instructions | How to solve normalize ignore paths |
| `X1` | References | Tried: normalize-paths-before-ignore-check |
| `X2` | References | Tried: normalize-subfilepath-in-recursive-loop |
| `X3` | References | Tried: normalize-in-is-ignored-file-helper |
| `X4` | References | Sources consulted for normalize ignore paths |
| `X5` | References | What has been investigated about normalize ignore paths |
| `X6` | References | Where research on this subject stands |
| `X48` | References | Tried: normalize_paths_before_ignore_check |
| `X49` | References | Tried: normalize_subfilepath_in_recursive_loop |





























































































## Instructions

### I1 — How to evaluate a change to normalize ignore paths

Figure of merit: **target_tests_passing** (max, target 1.0).

Measured by: Run hidden target tests that verify ignore-paths is respected when --recursive=y is used. The metric is the fraction of target tests passing (0.0 to 1.0). Since we cannot see the tests, we validate with: (1) manual reproduction showing src/gen/* is ignored with --recursive=y and ignore-paths pattern; (2) existing pylint test suite passes with no regressions.

Cases differ along: config_location, ignore_pattern_type, recursive_flag.

### I2 — How to solve normalize ignore paths

Try these in order. Ranked by measured **target_tests_passing** (max, target 1.0). Each one's hypothesis and evidence is in the matching `Tried:` reference on this skill.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. **normalize-paths-before-ignore-check** — target_tests_passing 1.000, potential — Normalize paths using os.path.normpath() before checking against ignore-paths patterns. This ensures that path
2. **normalize-in-is-ignored-file-helper** — target_tests_passing 1.000, potential — Normalize the element path at the start of _is_ignored_file() helper function (line 52-55), so all callers ben
3. **normalize-subfilepath-in-recursive-loop** — target_tests_passing 0.900, potential — Normalize subfilepath before checking against ignore patterns in the recursive directory traversal loop (lines

## Rules

## References

### X1 — Tried: normalize-paths-before-ignore-check

Normalize paths using os.path.normpath() before checking against ignore-paths patterns. This ensures that paths like ./some/path, some/path, and some//path are all treated consistently when matching against ignore-paths regex patterns.

**Hypothesis**: The bug exists because paths discovered during recursive traversal are not normalized before being matched against ignore-paths regex patterns. Different representations of the same path (with/without ./, with // instead of /) fail to match the patterns. Normalizing paths before the ignore check will make all equivalent path representations match consistently.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: normalize-subfilepath-in-recursive-loop

Normalize subfilepath before checking against ignore patterns in the recursive directory traversal loop (lines 143-146 in expand_modules.py)

**Hypothesis**: When recursively discovering files in a directory, subfilepaths are not normalized before being matched against ignore_list_paths_re patterns. This causes patterns written for normalized paths to fail matching against unnormalized discovered paths.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: normalize-in-is-ignored-file-helper

Normalize the element path at the start of _is_ignored_file() helper function (line 52-55), so all callers benefit from consistent normalization without needing to normalize at each call site.

**Hypothesis**: The bug exists because paths are checked against ignore patterns without normalization. By normalizing the element parameter at the entry point of _is_ignored_file() (line 55: element = os.path.normpath(element)), all subsequent pattern checks will operate on normalized paths. This is more maintainable than normalizing at multiple call sites. Would be falsified if normalization at this point break

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Sources consulted for normalize ignore paths

- https://github.com/pylint-dev/pylint/pull/7080 - Official fix PR by matusvalo that was merged to resolve issue #6964, which is the same issue described in the task. The PR shows the exact change neede
- https://github.com/pylint-dev/pylint/pull/7080/files - Official merged fix by matusvalo. The actual fix adds `element = os.path.normpath(element)` at line 55 in _is_ignored_file() function in pylint/l

### X5 — What has been investigated about normalize ignore paths

Ground already covered by research on this subject.

- **recursive-implementation** — How does pylint implement recursive directory traversal and where does it collect files?
  Looked in: pylint source code, specifically the recursive flag handling and file discovery logic
- **ignore-paths-application** — Where and when are ignore-paths patterns applied during file collection?
  Looked in: Configuration loading and file filtering logic in pylint
- **config-loading-order** — How does pylint load and merge configuration from different sources (pyproject.toml, pylintrc, setup.cfg)?
  Looked in: Configuration parsing and initialization code
- **pattern-matching-logic** — How are ignore-paths patterns (regex/glob/literal) matched against discovered file paths?
  Looked in: Path matching utilities and ignore logic
- **known-issues-fixes** — Has this bug or similar recursive+ignore bugs been reported/fixed before in pylint or similar linters?
  Looked in: pylint issue tracker, commit history, related projects (flake8, mypy)

### X6 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **tests_passed** (max, target 1.0).

**Still open**
- normalize-in-is-ignored-file-helper (potential)
- normalize_paths_before_ignore_check (potential)
- normalize_subfilepath_in_recursive_loop (potential)
- normalize-paths-before-ignore-check (potential tests_passed=0.0)
- (no files changed) (potential)
- normalize_in_is_ignored_file_helper (potential)

**Where the detail is**
- normalize-in-is-ignored-file-helper: https://github.com/pylint-dev/pylint/pull/7080
- normalize_paths_before_ignore_check: Official PR #7080: https://github.com/pylint-dev/pylint/pull/7080
- normalize_subfilepath_in_recursive_loop: Official PR #7080: https://github.com/pylint-dev/pylint/pull/7080
- normalize-paths-before-ignore-check: Official PR #7080: https://github.com/pylint-dev/pylint/pull/7080
- (no files changed): benchmark attempt
- normalize_in_is_ignored_file_helper: https://github.com/pylint-dev/pylint/pull/7080
- full record: research topic `pylint-dev__pylint-7080` (via research_status, only if this summary is not enough)### X47 — Tried: normalize_in_is_ignored_file_helper

Add os.path.normpath(element) directly in _is_ignored_file helper function.

**Hypothesis**: Normalizing element inside the helper ensures all ignore checks use consistent paths.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X48 — Tried: normalize_paths_before_ignore_check

Add os.path.normpath(element) before checking ignore patterns in _is_ignored_file.

**Hypothesis**: Normalizing the file path before ignore-paths matching ensures patterns are applied correctly for recursive file discovery.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X49 — Tried: normalize_subfilepath_in_recursive_loop

Normalize subfilepath during recursive directory traversal before applying ignore-paths patterns.

**Hypothesis**: Applying os.path.normpath to each subfilepath during recursion ensures ignore-paths patterns match correctly.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.
