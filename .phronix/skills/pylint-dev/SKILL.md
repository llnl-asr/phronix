---
name: pylint-dev
description: Research on pylint dev. Covers in pylint/lint/pylinter.py _discover_files, is _is_ignored_file only applied to the walked directory root (and __init__.py packages), while individual non-package files yielded via the 'yield from (os.path.join(root,file) ...)' branch are never checked against ignore_paths/ignore/ignore_patterns? Confirm by tracing the code path with the issue's src/gen example.; what is the exact signature and matching semantics of _is_ignored_file (in expand_modules.py) — does it take a path and check basename against ignore, ignore-patterns against basename, and ignore-paths r
subject: pylint-dev
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to pylint dev |
| `I2` | Instructions | How to solve pylint dev |
| `I4` | Instructions | Steps to solve pylint dev |
| `I5` | Instructions | Fallback approaches for pylint dev |
| `R2` | Rules | Fix this in In PyLinter._discover_files, apply _is_ignored_file to each |
| `R3` | Rules | Fix this in CONFIRMED fix for the actual #7080 bug. In _discover_files, |
| `R4` | Rules | Fix this in CONFIRMED root cause: in PyLinter._discover_files (pylint/li |
| `X27` | References | Tried: fix_discover_files_filter_individual_files |
| `X28` | References | Tried: normpath-in-is-ignored-file |
| `X29` | References | Tried: per_file_ignore_check_plus_keep_dir_pruning-r1 |
| `X30` | References | Tried: normpath-plus-discover-files-per-file-check |
| `X31` | References | Tried: add-per-file-is_ignored_file-check-in-else-branch |
| `X32` | References | Tried: ignore_paths_matching_directory_name_only |
| `X33` | References | Sources consulted for pylint dev |
| `X34` | References | Tried: fix-discover-files-filter-per-file |
| `X35` | References | Tried: change-is-ignored-file-signature |
| `X36` | References | Tried: remove-directory-level-skip-subtrees-check |
| `X37` | References | What has been investigated about pylint dev |
| `X38` | References | Where research on this subject stands |




















































































## Instructions

### I1 — How to evaluate a change to pylint dev

Figure of merit: **fraction_of_discover_files_cases_correctly_included_or_excluded** (max, target 1.0).

Measured by: For each corpus instance, build the described directory tree in a scratch dir, set ignore-paths/ignore/ignore-patterns config as specified, call PyLinter._discover_files(['.']) (or run `pylint --recursive=y .` via subprocess) and check whether the set of yielded/checked files exactly matches the expected included-file list (files under ignore-paths patterns must be absent; files outside must be pr

Cases differ along: expect_excluded, file_depth, match_mechanism, path_form, target_type.

### I2 — How to solve pylint dev

Try these in order, ONE at a time. Ranked by measured **fraction_of_discover_files_cases_correctly_included_or_excluded** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A11` **per_file_ignore_check_plus_keep_dir_pruning-r1** — fraction_of_discover_files_cases_correctly_included_or_excluded unmeasured, potential — Add per-file _is_ignored_file check in _discover_files' non-package else branch, while kee

...and 9 lower-ranked approach(es); see `research_rank`.### R1 — Fix this in Add per-file _is_ignored_file check in _discover_files' non-

Add per-file _is_ignored_file check in _discover_files' non-package else branch, while keeping the existing directory-level skip_subtrees/_is_ignored_file(root,...) check unchanged for subtree pruning perf and package __init__.py handling.

Why it holds: The dir-level check and a new per-file check are not redundant: dir-level check prunes whole subtrees (os.walk still descends without it, wasting per-file regex work) and handles package units (__init__.py yields whole dir, never enumerates files); per-file check is needed because --ignore-paths patterns targeting individual filenames are currently never tested against files yielded in the non-pac

Confirmed on held-out instances (test 1/1, train 2/2, validate 1/1).

### R2 — Fix this in In PyLinter._discover_files, apply _is_ignored_file to each

In PyLinter._discover_files, apply _is_ignored_file to each individual .py file yielded in the non-package branch (currently only applied to os.walk root and __init__.py package dirs), so ignore/ignore-patterns/ignore-paths regexes written against full file paths actually exclude loose files under a

Why it holds: _is_ignored_file in _discover_files (pylint/lint/pylinter.py ~L585-619) is only called on os.walk's `root` (for subtree-skip and for __init__.py package yields), never on the individual file paths produced by `yield from (os.path.join(root, file) ...)` for non-package files. This means --ignore-paths/--ignore/--ignore-patterns regexes matching a full file path (e.g. `.*/gen/.*\.py$`) fail to exclu

Confirmed on held-out instances (test 3/3, train 22/22, validate 2/2).

### I4 — Steps to solve pylint dev

The steps that solve pylint dev, in order. Run them.

1. `locate_discover_files_ignore_check(...)` — Locate _discover_files and _is_ignored_file
2. `apply_normpath_ignore_fix(...)` — Apply normpath fix in expand_modules.py
3. `apply_discover_files_per_file_ignore_patch(...)` — Add per-file ignore check in the else branch
4. `add_ignore_path_recursive_current_dir_test(...)` — Add the real hidden regression test
5. `verify_discover_files_excludes_ignored(...)` — Verify _discover_files output directly excludes ignored files
6. `run_pylint_ignore_tests(...)` — Run existing recursive/ignore-path tests plus the new one
7. `check_no_new_regressions(...)` — Confirm no new regressions in the full self-test suite### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **fraction_of_discover_files_cases_correctly_included_or_excluded** (max, target 1.0).

**Established**
- filter_individual_files_in_discover_files (confirmed fraction_of_discover_files_cases_correctly_included_or_excluded=1.0)
- fix_discover_files_filter_individual_files (confirmed fraction_of_discover_files_cases_correctly_included_or_excluded=1.0)
- add-per-file-is_ignored_file-check-in-else-branch (confirmed fraction_of_discover_files_cases_correctly_included_or_excluded=1.0)
- ignore_paths_matching_directory_name_only (potential)
- fix-discover-files-filter-per-file (potential)
- normpath-in-is-ignored-file (potential)

**Still open**
- remove-directory-level-skip-subtrees-check (potential)
- change-is-ignored-file-signature (potential)
- pylint/lint/pylinter.py (potential fraction_of_discover_files_cases_correctly_included_or_excluded=0.0)
- per_file_ignore_check_plus_keep_dir_pruning-r1 (potential)
- aspect not yet answered: existing_test_coverage_for_recursive_ignore
- aspect not yet answered: changelog_and_prior_fix_convention

**Ruled out**

...and 9 more line(s); see the full record.### X26 — Tried: remove-directory-level-skip-subtrees-check

REFUTED as a redundancy claim: removing/replacing the directory-level skip_subtrees + _is_ignored_file(root,...) check with a per-file-only check would reintroduce two regressions — loss of perf pruning (os.walk still descends into ignored subtrees, just walked and regex-tested per file instead of p

**Hypothesis**: Hypothesis: a per-file ignore check alone could replace the directory-level skip_subtrees/_is_ignored_file(root,...) check as redundant. Falsified by: tracing that the two checks operate on different granularities/purposes (perf pruning of whole subtrees vs. package unit yielding) that a per-file check cannot substitute for.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X27 — Tried: fix_discover_files_filter_individual_files

CONFIRMED root cause: in PyLinter._discover_files (pylint/lint/pylinter.py ~585-619), _is_ignored_file is only ever called on the walked directory `root` (once for the skip-subtree/ignore check, once implicitly via the __init__.py-package yield), never on individual non-package .py files produced by

**Hypothesis**: If _is_ignored_file is applied only to directory roots and not to individual file paths in the non-package yield-from branch, then an ignore-paths/ignore/ignore-patterns regex written to match a file's full path (rather than matching the directory name itself) will fail to exclude that file even though it should. Falsified if such a regex still excludes the file, or if _is_ignored_file turns out t

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X28 — Tried: normpath-in-is-ignored-file

In pylint/lint/expand_modules.py::_is_ignored_file, add `element = os.path.normpath(element)` as the first line before computing basename/regex matches. No changes to pylinter.py's _discover_files needed.

**Hypothesis**: The reported bug is not that individual files skip the ignore check (they don't — expand_modules() already calls _is_ignored_file on every discovered file/module path downstream of _discover_files). The real bug is that _is_ignored_file receives paths with irregular separators/segments (mixed '/' and '\\' on Windows from combining a user-supplied 'src/' arg with os.walk's os.sep-based os.path.join

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X29 — Tried: per_file_ignore_check_plus_keep_dir_pruning-r1

Add per-file _is_ignored_file check in _discover_files' non-package else branch, while keeping the existing directory-level skip_subtrees/_is_ignored_file(root,...) check unchanged for subtree pruning perf and package __init__.py handling.

Revision 1: Add os.path.normpath() to the path/element befo

**Hypothesis**: Add os.path.normpath() to the path/element before matching against ignore-paths — either inside _is_ignored_file (pylint/lint/expand_modules.py) so every call site (both the directory-root check and the new per-file check in pylinter.py::_discover_files) benefits automatically, or immediately before each _is_ignored_file() call site in _discover_files. Keep A1's per-file check in the else branch (

**Status**: potential (test 1/1, train 2/2, validate 1/1). Investigated already — extend this rather than re-deriving it.

### X30 — Tried: normpath-plus-discover-files-per-file-check

Combine the normpath fix in expand_modules.py::_is_ignored_file (A9) with also normalizing the path fed into _is_ignored_file inside pylinter.py::_discover_files (both the directory-root check and a new per-file check in the else branch), so that any hidden test inspecting _discover_files()'s output

**Hypothesis**: If the hidden target test calls PyLinter._discover_files() directly and asserts on its yielded file list (as tests/lint/unittest_lint.py::test_recursive_ignore already does for run.linter._iterate_file_descrs(tuple(run.linter._discover_files(...)))), the normpath-only fix in expand_modules is sufficient since that test chains through _iterate_file_descrs -> expand_modules. But if some hidden test 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X31 — Tried: add-per-file-is_ignored_file-check-in-else-branch

CONFIRMED fix for the actual #7080 bug. In _discover_files, the else branch (non-package directory) yields individual *.py files straight from `files` without ever testing them against _is_ignored_file, so --ignore-paths regexes targeting specific files (not directory components) silently have no ef

**Hypothesis**: Hypothesis: individual .py files discovered under a non-package directory are never checked against ignore-paths, causing #7080. Confirmed by direct repro before/after the fix showing the ignored file disappears from _discover_files output while non-matching files and packages are still yielded.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X32 — Tried: ignore_paths_matching_directory_name_only

REFUTED as the general fix / not itself buggy: when the ignore-paths regex is written to match the directory name itself (e.g. `.*gen.*` matching a `.../src/gen` root string) rather than requiring trailing path content, the existing root-level check in _discover_files already skips the whole subtree

**Hypothesis**: If the bug were a general failure of ignore-paths rather than a gap specific to individual-file yields, then a directory-name-style regex would also fail to exclude the subtree. It does not fail — the subtree is correctly skipped — so this rules out "ignore-paths is entirely non-functional" as the root cause.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X33 — Sources consulted for pylint dev

- pylint/lint/pylinter.py _discover_files; pylint/lint/expand_modules.py _is_ignored_file; issue #7080 (ignore-paths not respected for individual files under recursive discovery)

### X34 — Tried: fix-discover-files-filter-per-file

Confirmed fix: in pylinter.py::_discover_files, the else branch (non-package .py files under os.walk) must also call _is_ignored_file() per file, not just per directory root. Reproduced the bug (ignore-paths regex matching a file did not exclude it under --recursive=y) and verified the fix removes i

**Hypothesis**: _is_ignored_file is path-type agnostic (no dir/file branch inside it — just os.path.basename + two regex checks), so it can be called unmodified on each discovered file path (os.path.join(root, file)) inside _discover_files's os.walk loop, and doing so will make --ignore/--ignore-patterns/--ignore-paths correctly filter individual files under --recursive=y. Falsifiable by: reproducing with ignore_

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X35 — Tried: change-is-ignored-file-signature

Refuted as unnecessary: no need to change _is_ignored_file's signature or add file/dir-distinguishing logic to support per-file filtering. The function already takes a generic `element: str` and does only os.path.basename() + two regex checks, with no branch on whether element is a file or directory

**Hypothesis**: Hypothesis considered and rejected: that filtering individual files under --recursive=y would require modifying _is_ignored_file itself (e.g. adding a path-type parameter or separate file-vs-dir logic). Refuted by reading the function body directly: it is fully path-type agnostic already.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### I5 — Fallback approaches for pylint dev

If the leading approach fails, these were also measured, ranked by the same metric.

**`A2` filter_individual_files_in_discover_files** — fraction_of_discover_files_cases_correctly_included_or_excluded 1.000
  1. Locate PyLinter._discover_files in pylint/lint/pylinter.py (judgement)
  2. Confirm _is_ignored_file is path-type agnostic (judgement)
  3. Add per-file ignore check to the non-package yield branch (judgement)
  4. Build a corpus of directory-tree scenarios covering all thre (judgement)
  5. Run each scenario directly against PyLinter._discover_files (judgement)
  6. Run the existing test suite for regressions (judgement)

**`A4` fix_discover_files_filter_individual_files** — fraction_of_discover_files_cases_correctly_included_or_excluded 1.000
  1. Locate PyLinter._discover_files (judgement)
  2. Confirm _is_ignored_file is path-type agnostic (judgement)
  3. Add per-file ignore check to the non-package yield branch (judgement)
  4. `discover_files_ignore_scenarios(...)`
  5. `run_pylint_ignore_tests(...)`
  6. Record trials and pipeline (judgement)

**`A5` add-per-file-is_ignored_file-check-in-else-branch** — fraction_of_discover_files_cases_correctly_included_or_excluded 1.000
  1. `mcp__phronix__locate_discover_files_ignore_check(...)`

...and 6 more line(s); see `research_rank`.## Rules

### R3 — Fix this in CONFIRMED fix for the actual #7080 bug. In _discover_files,

CONFIRMED fix for the actual #7080 bug. In _discover_files, the else branch (non-package directory) yields individual *.py files straight from `files` without ever testing them against _is_ignored_file, so --ignore-paths regexes targeting specific files (not directory components) silently have no ef

Why it holds: Hypothesis: individual .py files discovered under a non-package directory are never checked against ignore-paths, causing #7080. Confirmed by direct repro before/after the fix showing the ignored file disappears from _discover_files output while non-matching files and packages are still yielded.

Confirmed on held-out instances (test 1/1, train 2/3, validate 1/1).

### R4 — Fix this in CONFIRMED root cause: in PyLinter._discover_files (pylint/li

CONFIRMED root cause: in PyLinter._discover_files (pylint/lint/pylinter.py ~585-619), _is_ignored_file is only ever called on the walked directory `root` (once for the skip-subtree/ignore check, once implicitly via the __init__.py-package yield), never on individual non-package .py files produced by

Why it holds: If _is_ignored_file is applied only to directory roots and not to individual file paths in the non-package yield-from branch, then an ignore-paths/ignore/ignore-patterns regex written to match a file's full path (rather than matching the directory name itself) will fail to exclude that file even though it should. Falsified if such a regex still excludes the file, or if _is_ignored_file turns out t

Confirmed on held-out instances (test 1/1, train 3/3, validate 1/1).

## References

### X36 — Tried: remove-directory-level-skip-subtrees-check

REFUTED as a redundancy claim: removing/replacing the directory-level skip_subtrees + _is_ignored_file(root,...) check with a per-file-only check would reintroduce two regressions — loss of perf pruning (os.walk still descends into ignored subtrees, just walked and regex-tested per file instead of p

**Hypothesis**: Hypothesis: a per-file ignore check alone could replace the directory-level skip_subtrees/_is_ignored_file(root,...) check as redundant. Falsified by: tracing that the two checks operate on different granularities/purposes (perf pruning of whole subtrees vs. package unit yielding) that a per-file check cannot substitute for.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X37 — What has been investigated about pylint dev

Ground already covered by research on this subject.

- **root_cause_in_discover_files** — In pylint/lint/pylinter.py _discover_files, is _is_ignored_file only applied to the walked directory root (and __init__.py packages), while individual non-package files yielded via the 'yield from (os
  Looked in: pylint/lint/pylinter.py _discover_files (~line 585-619), pylint/lint/expand_modules.py _is_ignored_file
- **is_ignored_file_signature_and_reuse** — What is the exact signature and matching semantics of _is_ignored_file (in expand_modules.py) — does it take a path and check basename against ignore, ignore-patterns against basename, and ignore-path
  Looked in: pylint/lint/expand_modules.py _is_ignored_file definition and its other call site in expand_modules()
- **skip_subtrees_still_needed_for_dirs** — If per-file filtering is added, should the existing directory-level skip_subtrees/_is_ignored_file check on os.walk roots still be kept (for performance/pruning of entire subtrees and for package dirs
  Looked in: pylint/lint/pylinter.py _discover_files

...and 4 more line(s) of ground covered.

### X38 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **fraction_of_discover_files_cases_correctly_included_or_excluded** (max, target 1.0).

**Established**
- filter_individual_files_in_discover_files (confirmed fraction_of_discover_files_cases_correctly_included_or_excluded=1.0)
- fix_discover_files_filter_individual_files (confirmed fraction_of_discover_files_cases_correctly_included_or_excluded=1.0)
- add-per-file-is_ignored_file-check-in-else-branch (confirmed fraction_of_discover_files_cases_correctly_included_or_excluded=1.0)
- ignore_paths_matching_directory_name_only (potential)
- fix-discover-files-filter-per-file (potential)
- normpath-in-is-ignored-file (potential)

**Still open**
- remove-directory-level-skip-subtrees-check (potential)
- change-is-ignored-file-signature (potential)
- pylint/lint/pylinter.py (potential fraction_of_discover_files_cases_correctly_included_or_excluded=0.0)
- pylint/lint/expand_modules.py, pylint/lint/pylinter.py (potential fraction_of_discover_files_cases_correctly_included_or_excluded=1.0)
- aspect not yet answered: existing_test_coverage_for_recursive_ignore
- aspect not yet answered: changelog_and_prior_fix_convention

**Ruled out**

...and 9 more line(s); see the full record.