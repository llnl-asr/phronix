---
name: discover-files
description: Research on pylint's PyLinter._discover_files / expand_modules ignore-paths handling under --recursive=y, and where research on it stands.
subject: discover-files
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to discover files |
| `I2` | Instructions | How to solve discover files |
| `I4` | Instructions | Steps to solve discover files |
| `I5` | Instructions | Fallback approaches for discover files |
| `R3` | Rules | Fix this in Normalize the path string form (e.g. always relative to invo |
| `R4` | Rules | X42 confirmed refuted — update its stale "potential" status |
| `X36` | References | Sources consulted for discover files |
| `X37` | References | What has been investigated about discover files |
| `X41` | References | Tried: separator-normalization-windows-posix |
| `X42` | References | Tried: switch-match-to-fullmatch |
| `X43` | References | Tried: expand-modules-redundant-check-theory |
| `X44` | References | Tried: coerce-dimensionless-in-function-branch |
| `X45` | References | Tried: raise-on-non-dimensionless-function-arg |
| `X46` | References | Tried: pylint-ignore-paths-contamination-mismatch |
| `X49` | References | Tried: fix-check-file-paths-in-discover-files |
| `X50` | References | Tried: fix-discover-files-match-root-with-trailing-sep |
| `X51` | References | Tried: unit-test-is-ignored-file-windows-path-string |
| `X52` | References | X41 re-confirmed refuted — do not retune separator normalization |
| `X53` | References | Tried: expand_modules_redundant_check_theory |
| `X54` | References | Tried: absolute_path_defeats_anchored_ignore_paths_regex |
| `X55` | References | Where research on this subject stands |
| `X58` | References | Tried: prune-oswalk-dirs-in-place |
| `X59` | References | Tried: check-each-discovered-file-against-ignore-paths |















































































































































## Instructions

### I1 — How to evaluate a change to discover files

Figure of merit: **ignore_paths_recursive_accuracy** (max, target 1.0).

Measured by: Fraction of corpus instances where running `pylint --recursive=y <target>` with an `ignore-paths` regex configured in pyproject.toml/pylintrc produces the expected set of checked modules: files/dirs matching an ignore-paths pattern must NOT appear in the linted-module list (no 'Module X' report header, no errors emitted for them), while files/dirs that do not match must still appear and be linted.

Cases differ along: config_source, ignore_scope, path_separator_style, target_kind.

### I2 — How to solve discover files

Try these in order, ONE at a time. Ranked by measured **ignore_paths_recursive_accuracy** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A2` **fix-normalize-path-form-across-call-sites** — ignore_paths_recursive_accuracy 1.000, confirmed — Normalize the path string form (e.g. always relative to invocation cwd, always POSIX separ
2. `A1` **fix-discover-files-match-root-with-trailing-sep** — ignore_paths_recursive_accuracy 0.000, potential — In pylint/lint/pylinter.py::_discover_files, when checking a walked directory `root` again

...and 14 lower-ranked approach(es); see `research_rank`.### X35 — Tried: check-each-discovered-file-against-ignore-paths

In pylint/lint/pylinter.py _discover_files, in addition to (or instead of) checking the bare directory root, also run _is_ignored_file(os.path.join(root, file), ...) for each individual .py file before yielding it in the non-package (no __init__.py) branch at lines 612-617, so ignore-paths patterns 

**Hypothesis**: The root cause is that _discover_files only ever checks the directory root against ignore_paths and never the individual files it yields in the non-package branch (line 612-617) — unlike expand_modules.py's get_module_files loop, which does check subfilepath against ignore_list_paths_re. If true, adding a per-file check here closes the gap regardless of whether the directory-level trailing-separat

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X36 — Sources consulted for discover files

- issue.md reproduction (src/gen/*.py with no __init__.py under --recursive=y) + direct reading of pylint/lint/pylinter.py:585-617 this session

### X37 — What has been investigated about discover files

Ground already covered by research on this subject.

- **discover_files_ignore_check** — In PyLinter._discover_files (pylint/lint/pylinter.py ~585-619), _is_ignored_file is called only on `root` per os.walk iteration and never on the individual file paths yielded from `files`; does this m
  Looked in: pylint/lint/pylinter.py _discover_files
- **expand_modules_vs_discover_files_paths** — When --recursive=y is set, check() calls self._discover_files() first and then passes results into expand_modules/_iterate_file_descrs; does expand_modules's own _is_ignored_file check become redundan
  Looked in: pylint/lint/pylinter.py check(), pylint/lint/expand_modules.py expand_modules
- **regex_anchoring_relative_vs_absolute** — Does the ignore-paths regex match against absolute paths, paths relative to cwd, or paths relative to the linted root, and does os.walk's root/file path form (e.g. 'src/gen' vs 'src\gen\about.py') m
  Looked in: pylint/lint/expand_modules.py _is_in_ignore_list_re, pylint/config option parsing for ignore-paths
- **existing_test_coverage_gap** — What do the existing tests in tests/lint/test_expand_modules.py and tests/test_self.py already assert about ignore-paths with --recursive, and which of the corpus's negative/positive cases are NOT alr

...and 1 more line(s) of ground covered.### X40 — Tried: normalize-element-before-ignore-paths-match-cwd-dot-prefix

In pylint/lint/expand_modules.py::_is_ignored_file, also match os.path.normpath(element) against ignore_list_paths_re (in addition to the raw element). Reproduced and fixed the exact judged failure: running `pylint --recursive=y .` from inside a directory containing ignored_subdirectory/failing.py w

**Hypothesis**: The exact failure the last attempt was judged on (test_ignore_path_recursive_current_dir) is caused by os.walk('.') producing root paths like './ignored_subdirectory' when pylint is invoked recursively with '.' as the target; an anchored ignore-paths regex written without a leading './' (as pylint's own docs/tests write them, e.g. ^ignored_subdirectory/.*$) then never matches. Normalizing the path

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X41 — Tried: separator-normalization-windows-posix

REFUTED / already fixed upstream. Hypothesized that Windows (\\) vs POSIX (/) path separator mismatch in ignore-paths regex matching was the cause. Confirmed at HEAD of this checkout that pylint/config/argument.py::_regexp_paths_csv_transfomer already compiles every ignore-paths pattern as `<windows

**Hypothesis**: Separator normalization (POSIX vs Windows) causes the reported ignore-paths failure. REFUTED: code already exists and handles this at HEAD; the actual bug is the directory-vs-file-suffix pattern mismatch and relative-vs-absolute argument mismatch (see other approaches).

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X42 — Tried: switch-match-to-fullmatch

Considered and NOT pursued further: switching ignore-paths regex matching from re.Pattern.match (prefix-anchored) to fullmatch. Not identified as the cause of the reported bug — .match() is used consistently everywhere via _is_in_ignore_list_re, and users are expected to write their own trailing `.*

**Hypothesis**: Possible surprise source: match() vs fullmatch() semantics could cause unintended partial matches. Not refuted outright but explicitly deprioritized/not investigated further — the notes treat this as orthogonal to the actual reported bug (directory-vs-file pattern mismatch, relative-vs-absolute mismatch).

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X43 — Tried: expand-modules-redundant-check-theory

Theory that expand_modules's _is_ignored_file becomes redundant/unreachable after _discover_files under --recursive, so ignore-paths never gets applied there. Ruled out by direct instrumentation.

**Hypothesis**: If true, _discover_files' directory-root-level ignore check would already exclude everything expand_modules's file-level check would exclude, making the latter dead code for recursively-discovered inputs; false if expand_modules's check still fires and matters for cases discover_files misses.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X44 — Tried: coerce-dimensionless-in-function-branch

In UnitSystem._collect_factor_and_dimension's Function branch (sympy/physics/units/unitsystem.py, ~lines 192-196), for each collected arg dimension, coerce it to Dimension(1) when self.get_dimension_system().is_dimensionless(dim) is True — mirroring what the Pow branch (~167-172) already does for it

**Hypothesis**: The Function branch never checks is_dimensionless() on its args' dimensions the way the Pow branch does, so a dimensionless-but-not-literal-Dimension(1) argument (e.g. built from unit ratios like second/(farad*ohm)) is passed through as its raw non-trivial Dimension object; this later fails equality against Dimension(1) in the Add branch, causing the reported ValueError. Coercing dimensionless arg

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X45 — Tried: raise-on-non-dimensionless-function-arg

REFUTED candidate: make the Function branch strict — raise ValueError whenever any argument's dimension is not dimensionless, instead of selectively coercing dimensionless args to Dimension(1) and leaving non-dimensionless args alone.

**Hypothesis**: A stricter Function branch requiring ALL args of a Function to be dimensionless would be cleaner. REFUTED by sympy/physics/units/tests/test_quantities.py::test_factor_and_dimension (~line 353-356): pH = -log(cH) where cH has dimension amount_of_substance/volume (not dimensionless) is an existing, currently-passing case that expects a non-dimensionless result to propagate rather than raise uncondit

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X46 — Tried: pylint-ignore-paths-contamination-mismatch

Not applicable to this topic. The 13 pylint ignore-paths/_discover_files approaches previously recorded under this topic key (fix-discover-files-match-root-with-trailing-sep, fix-normalize-path-form-across-call-sites, etc.) describe pylint/lint/pylinter.py internals from a sibling phronix task (pyli

**Hypothesis**: N/A — this is a record of a data-contamination artifact, not a candidate fix. Verified by grep: no pylint/, no ignore-paths references in this repo tree.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### I4 — Steps to solve discover files

The steps that solve discover files, in order. Run them.

1. `probe_end_to_end_recursive_lint(...)` — Reproduce the failure
2. `probe_find_call_sites(...)` — Locate every ignore-paths call site
3. **Patch: normalize the path string before matching** (judgement — no tool for this)
   In pylint/lint/expand_modules.py::_is_ignored_file, also try _is_in_ignore_list_re(os.path.normpath(element), ignore_list_paths_re) in addition to the raw element. Apply the same normalization to subf
4. `probe_end_to_end_recursive_lint(...)` — Verify the exact reported/judged scenario end-to-end
5. `probe_run_pytest_selection(...)` — Run existing ignore-path unit/functional tests
6. `probe_run_pytest_selection(...)` — Rule out unrelated failures as pre-existing### X48 — Tried: regression-test-anchored-ignore-paths-nonpackage-subdir

Add a test that runs Run()/_discover_files end-to-end with --recursive=y over a fixture containing a non-package subdirectory 2+ levels deep, using an anchored ignore-paths regex (e.g. ^subdir/.*) rather than the loose .*name.* patterns existing tests use. This is the coverage gap that maps to the a

**Hypothesis**: Existing tests (test_ignore_recursive/test_ignore_pattern_recursive/test_ignore_path_recursive in tests/test_self.py, and unittest_expand_modules.py's test_expand_modules_with_ignore) only exercise loose substring regexes and/or call expand_modules() directly, never _discover_files with an anchored pattern — so a new anchored-pattern test would newly exercise the _discover_files path-matching code

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X49 — Tried: fix-check-file-paths-in-discover-files

CONFIRMED empirically, not just from reading. Built a test tree (src/gen/badfile.py, src/other/good.py) with ignore_paths matching `^.../src/gen/.*$`; linter._discover_files() returned badfile.py unfiltered on baseline. Fix: in the non-init "yield from files" branch, also call _is_ignored_file(os.pa

**Hypothesis**: In PyLinter._discover_files (pylint/lint/pylinter.py ~585-619), _is_ignored_file is called only on `root` per os.walk iteration, never on individual file paths in the non-__init__.py branch. Prediction: a .py file inside a non-ignored directory whose own path matches ignore-paths/ignore_patterns will still be yielded (bug), and this would be falsified if the file paths were checked elsewhere in th

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X50 — Tried: fix-discover-files-match-root-with-trailing-sep

In pylint/lint/pylinter.py::_discover_files, when checking a walked directory `root` against ignore_paths, also try matching `root + os.sep` (in addition to bare `root`) so patterns like `^src/gen/.*$` (written by users to match files) also match the bare directory itself before recursion decides to

**Hypothesis**: The bug is that `_discover_files` calls `_is_ignored_file(root, ...)` with `root` a bare directory path (e.g. "src/gen", no trailing separator, no filename), but user ignore-paths patterns like `^src/gen/.*$` require a `/` plus at least one char after "gen" to match — so `re.match` fails on the bare directory and the whole subtree is not skipped, even though every file within it should be ignored.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X51 — Tried: unit-test-is-ignored-file-windows-path-string

Unit-test _is_ignored_file (or the fixed equivalent) by directly calling it with a manufactured Windows-style path string (backslashes, e.g. src\gen\about.py) on any OS, rather than trying to reproduce Windows os.walk behavior in CI. Pairs with a fix that normalizes paths (os.path.normpath / pathlib

**Hypothesis**: If the root cause is Windows-path-separator handling (anchored regex ^src/gen/.*$ never matching a backslash-separated path returned by os.walk on Windows), a fix that normalizes separators can be regression-tested cross-platform by feeding a manufactured Windows-style string into the ignore-check function directly, without needing an actual Windows CI runner.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X52 — X41 re-confirmed refuted — do not retune separator normalization

X41 (separator-normalization-windows-posix) has now been independently re-checked and re-confirmed refuted; skip tuning it further. Same conclusion as [[pylint-ignore-paths#R1]] (Windows/POSIX separator handling was already solved upstream in pylint/config/argument.py::_regexp_paths_csv_transfomer at HEAD) — treat that block as canonical rather than re-deriving this.

### X53 — Tried: expand_modules_redundant_check_theory

REFUTED. Instrumented both functions directly and via full CLI (Run() with --recursive=y --ignore-paths=^src/gen/.*$ on src/ containing region_selection.py and src/gen/about.py). Both checks fire and inspect different things: _discover_files checks the directory root being walked (e.g. "src/gen", no

**Hypothesis**: When --recursive=y, PyLinter._discover_files() already filters via _is_ignored_file() (pylinter.py:600-607), so expand_modules()'s own _is_ignored_file() check (expand_modules.py:78-81) is redundant/unreachable for recursively-discovered files — and this is why ignore-paths regexes never get a chance to match.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### I5 — Fallback approaches for discover files

If the leading approach fails, these were also measured, ranked by the same metric.

**`A1` fix-discover-files-match-root-with-trailing-sep** — ignore_paths_recursive_accuracy 0.000
  1. Read judged failure (judgement)
  2. Reproduce the judged scenario directly (judgement)
  3. Trace os.walk root strings (judgement)
  4. Apply the trailing-sep patch (judgement)
  5. Re-run the reproduction (judgement)
  6. Diagnose and classify (judgement)

**`A12` prune-oswalk-dirs-in-place** — ignore_paths_recursive_accuracy unmeasured
  1. `probe_run_python_snippet(...)`
  2. Implement in-place dir pruning (judgement)
  3. Preserve __init__.py package semantics (judgement)
  4. `probe_run_pytest_selection(...)`
  5. `probe_run_pytest_selection(...)`

**`A13` check-each-discovered-file-against-ignore-paths** — ignore_paths_recursive_accuracy unmeasured
  1. `probe_find_call_sites(...)`
  2. `probe_run_python_snippet(...)`
  3. Add per-file ignore check in _discover_files (judgement)
  4. `probe_run_pytest_selection(...)`
  5. `probe_find_call_sites(...)`### R2 — X50 confirmed refuted — does not fix test_ignore_path_recursive_current_dir

X50 (fix-discover-files-match-root-with-trailing-sep: match `root + os.sep` in addition to bare `root`) has been tried and does NOT fix the judged failure test_ignore_path_recursive_current_dir. Update X50's status line from "potential" to refuted. Contrast with [[discover-files#X40]] (normalize-element-before-ignore-paths-match-cwd-dot-prefix), which does fix that same judged failure — X40 is the confirmed direction, X50 is not.

### R3 — Fix this in Normalize the path string form (e.g. always relative to invo

Normalize the path string form (e.g. always relative to invocation cwd, always POSIX separators) before matching against ignore_paths at every call site — _discover_files' `root`, expand_modules' `element`, and astroid's get_module_files walk results — so the same string form is checked everywhere r

Why it holds: The bug is that different call sites (_discover_files, expand_modules, astroid's get_module_files via os.walk) pass path strings in whatever form the caller's original argument took — relative if the user invoked `pylint src`, absolute if `pylint /abs/path/src` — and a single ignore-paths regex written by the user can only match one of those forms, so it silently fails for the other. Normalizing t

Confirmed on held-out instances (test 1/1, validate 1/1).

## References

### X54 — Tried: absolute_path_defeats_anchored_ignore_paths_regex

CONFIRMED as an actual reproduction of the bug, found incidentally while testing the (refuted) redundant-check theory. Run(['--recursive=y','--ignore-paths=^src/gen/.*$', os.path.abspath('src')]) leaks src/gen/about.py through; Run(['--ignore-paths=^src/gen/.*$', abspath]) (no --recursive) fails ide

**Hypothesis**: Passing an absolute path as the files_or_modules CLI argument causes expand_modules/modutils to produce absolute file paths in results, which a relative-style anchored ignore-paths regex (e.g. ^src/gen/.*$) can never match — this reproduces the reported bug and occurs independently of --recursive.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X55 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **ignore_paths_recursive_accuracy** (max, target 1.0).

**Established**
- fix-discover-files-match-root-with-trailing-sep (potential ignore_paths_recursive_accuracy=0.0)
- fix-normalize-path-form-across-call-sites (working ignore_paths_recursive_accuracy=1.0)
- expand_modules_redundant_check_theory (potential)
- absolute_path_defeats_anchored_ignore_paths_regex (potential)
- fix-check-file-paths-in-discover-files (potential)
- root-only-regex-trailing-content-mismatch (potential)

**Still open**
- regression-test-anchored-ignore-paths-nonpackage-subdir (potential)
- unit-test-is-ignored-file-windows-path-string (potential)
- prune-oswalk-dirs-in-place (potential)
- check-each-discovered-file-against-ignore-paths (potential)
- pylint/checkers/misc.py (potential ignore_paths_recursive_accuracy=1.0)
- aspect not yet answered: existing_test_coverage_gap

**Ruled out**
- separator-normalization-windows-posix (falsified ignore_paths_recursive_accuracy=0.0)
- switch-match-to-fullmatch (falsified ignore_paths_recursive_accuracy=0.0)
- expand-modules-redundant-check-theory (falsified ignore_paths_recursive_accuracy=0.0)

**Where the detail is**

...and 7 more line(s); see the full record.### X57 — Tried: root-only-regex-trailing-content-mismatch

CONFIRMED by direct regex testing: re.compile(r'^tmp/research/testproj/src/gen/.*$').search('tmp/research/testproj/src/gen') -> None, but .search('tmp/research/testproj/src/gen/badfile.py') -> match. This is a second, compounding failure mode alongside the file-path-never-checked bug: directories wh

**Hypothesis**: Even where _is_ignored_file(root, ...) IS invoked by os.walk, a typical user-authored ignore-paths regex like `^src/gen/.*$` (which requires a `/` followed by at least one more char to satisfy `.*`) will fail to match the bare directory path `src/gen` (no trailing separator+content), so such directories are never recognized as ignored via the root check alone.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X58 — Tried: prune-oswalk-dirs-in-place

In pylint/lint/pylinter.py _discover_files (around line 595), change os.walk(something) to os.walk(something) and mutate the yielded dirs list in-place each iteration (`dirs[:] = [d for d in dirs if not _is_ignored_file(os.path.join(root, d) + os.sep, ...)]`), so ignored subdirectories like src/gen 

**Hypothesis**: The bug is not just a matching-mechanics issue (missing trailing separator) but a discovery-order issue: os.walk already returns dirs for root='src', and checking ignore only on 'root' as it is visited (post-hoc, one level too late relative to trailing-sep patterns) is fragile. Actively pruning the dirs list before os.walk descends is more robust and mirrors how tools like git/flake8 implement pat

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X59 — Tried: check-each-discovered-file-against-ignore-paths

In pylint/lint/pylinter.py _discover_files, in addition to (or instead of) checking the bare directory root, also run _is_ignored_file(os.path.join(root, file), ...) for each individual .py file before yielding it in the non-package (no __init__.py) branch at lines 612-617, so ignore-paths patterns 

**Hypothesis**: The root cause is that _discover_files only ever checks the directory root against ignore_paths and never the individual files it yields in the non-package branch (line 612-617) — unlike expand_modules.py's get_module_files loop, which does check subfilepath against ignore_list_paths_re. If true, adding a per-file check here closes the gap regardless of whether the directory-level trailing-separat

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

## Rules

### R4 — X42 confirmed refuted — update its stale "potential" status

switch-match-to-fullmatch (X42) is no longer "potential, no trials recorded" — reported failing 3x now across measurement/tune/tuning stages, worked=0/failed=3. Treat X42 as refuted like X41/X50, not as an untried candidate.

Separately, this same approach name has also surfaced as a cross-topic contamination case (assigned to pylint-dev__pylint-5859, whose actual bug is the fixme/notes_rgx word-boundary issue, unrelated to ignore-paths) — that mismatch is tracked at [[pylint-dev-pylint-5859#R5]], distinct from this refutation-on-the-merits.
