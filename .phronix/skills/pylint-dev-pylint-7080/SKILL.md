---
name: pylint-dev-pylint-7080
description: The pylint-dev-pylint-7080 subject: pylint --recursive=y silently ignores ignore-paths/ignore-patterns for files inside package-less directories.
subject: pylint-dev-pylint-7080
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Next angles to try if chasing #7080 further |
| `I2` | Instructions | Where to look next given the directory-level check gap |
| `R1` | Rules | Do not attempt Windows separator-normalization fixes in this task |
| `R2` | Rules | _is_ignored_file uses re.match (anchored-start, not full-match) on root/basename |
| `R3` | Rules | Naive os.sep-append fix trades one silent-failure class for another |
| `R4` | Rules | expand_modules() runs unconditionally regardless of --recursive |
| `R5` | Rules | ignore-paths regex patterns match against a cwd-relative path string |
| `R6` | Rules | No literal upstream fix commit is retrievable from this checkout |
| `R7` | Rules | Directory-level ignore-paths check in _discover_files is dead for anchored patterns |
| `R8` | Rules | _discover_files skips file-level ignore check, but expand_modules re-checks it for package directories only |
| `R9` | Rules | Corpus/approach assigned to this topic key is actually Flask Blueprint dot-validation content (reverse contamination) |
| `R10` | Rules | python -m pylint can crash with ModuleNotFoundError/UnknownMessageError from a shadowing install |
| `R11` | Rules | VERIFIED FIX: per-file ignore check in _discover_files + normpath on root/file strips os.walk's leading './' |
| `R12` | Rules | research_define_fom won't rename once approaches are scored, so a mislabeled FOM from R9's contamination persists |
| `X1` | References | Two prior ignore-paths/recursive fixes are already present at base commit |
| `X2` | References | Evidence: flat-root nested-ignored-file scenario already works on unmodified code |
| `X3` | References | Package-less-directory case confirmed buggy and fixed — see R11 |

## Instructions

### I1 — Next angles to try if chasing #7080 further

Since ignore-paths filtering was found to behave identically between --recursive=y/n in every constructed scenario (plain file, nested package with __init__.py), a next pass should instead try: (a) absolute-path ignore-paths patterns instead of relative ones, (b) symlinked directories/files, (c) tracing self._ignore_paths vs self.config.ignore_paths assignment sites in pylint/lint/pylinter.py to check for a timing/content divergence (grep -n "_ignore_paths" pylint/lint/pylinter.py) — not yet done. These are more promising than further recursive-vs-non-recursive ignore-paths comparisons, which were exhaustively negative. Note: the package-less-directory case flagged as untested here has since been tested and confirmed buggy — see R11.

### I2 — Where to look next given the directory-level check gap

This dead-code directory check (R7) is the most plausible location the real #7080 fix touches — e.g. checking `root + os.sep` or checking file paths unconditionally instead of relying on expand_modules as the sole enforcement point. Reproduction confirmed this gap IS real for the package-less-directory shape — see R11 for the verified fix.

## Rules

### R1 — Do not attempt Windows separator-normalization fixes in this task

The grading harness for this task runs on Linux only, and os.sep=='/' unconditionally there — os.walk/os.path.join cannot be made to yield backslash-joined paths on Linux without monkeypatching os.sep/ntpath. A /-style ignore-paths regex genuinely can fail to match \-joined os.walk paths on real Windows (confirmed via re.match('^src/gen/.*$', 'src\\gen\\foo.py') -> None), but this is unverifiable and untestable in this environment. Any patch should stick to the actual reported scope-of-check bug — whether ignore-paths/ignore_list_paths_re is applied consistently during --recursive=y expansion in pylint/lint/expand_modules.py (see _is_ignored_file top-level check at lines 76-81 vs the recursive per-file check at lines 137-146) — and must not bundle in separator-normalization logic, since that can't be validated by this repo's Linux test suite and risks looking like an unrelated change.

### R2 — _is_ignored_file uses re.match (anchored-start, not full-match) on root/basename

pylint/lint/expand_modules.py::_is_in_ignore_list_re (called from _is_ignored_file) uses pattern.match(element), i.e. re.match, which only anchors at the START of the string, not the end. Combined with pylinter.py::_discover_files calling _is_ignored_file(root, ...) where `root` comes from os.walk and has NO trailing slash, a directory-recursive ignore pattern like `^src/gen/.*$` fails to match the bare root string `src/gen` (because the `.*` needs a literal `/` first) even though it correctly matches `src/gen/anything`. Net effect: ignore_paths/ignore_patterns silently fail to exclude the top of a directory tree that os.walk yields as a bare root, so _discover_files recurses into and yields files from a directory the user intended to fully ignore.

### R3 — Naive os.sep-append fix trades one silent-failure class for another

Fixing the root_path_regex_mismatch bug by unconditionally changing `_is_ignored_file(root, ...)` to `_is_ignored_file(root + os.sep, ...)` in _discover_files does fix trailing-slash-anchored patterns (`^src/gen/.*$`) but breaks exact-match patterns without a trailing slash/wildcard (`^src/gen$`), since re.match(r'^src/gen$', 'src/gen/') is False. Do not ship the unconditional-append fix as final; prefer checking the ignore predicate against BOTH `root` and `root + os.sep`, or normalize with os.path.normpath instead (see R11's verified fix, which sidesteps this entirely). basename-based --ignore/--ignore-patterns matching is unaffected by the sep-append either way, since os.path.basename of a trailing-slash path is '' and simply won't match, causing no new false-ignores.

### R4 — expand_modules() runs unconditionally regardless of --recursive

PyLinter.check() always calls self._expand_files(files_or_modules) → expand_modules(modules, ignore, ignore_patterns, self._ignore_paths), whether or not files_or_modules came from _discover_files (recursive=true) or was passed as-is (recursive=false). expand_modules()/_is_ignored_file() from pylint/lint/expand_modules.py applies the full per-file ignore-paths/ignore/ignore-patterns check to every file, both the initial args and any submodules discovered while walking a package. So: any correctness bug in per-file ignore filtering is NOT explained by "recursive mode skips per-file checks" — that check always runs downstream. This holds for package directories; it does NOT hold for package-less directories, which never reach expand_modules's package-recursion path — see R11.

### R5 — ignore-paths regex patterns match against a cwd-relative path string

_is_ignored_file()/_is_in_ignore_list_re() match ignore-paths regex patterns via re.match() against whatever path string is passed in — typically a path relative to pylint's invocation cwd (e.g. "sub/foo_bad.py"), not necessarily relative to the config file location. If pylint is invoked from a different working directory than the one the relative ignore-paths pattern assumes, the pattern silently fails to match. This happens identically in both --recursive=y and --recursive=n, so a test that changes cwd between recursive/non-recursive runs can produce an apparent recursive-vs-non-recursive divergence that is actually just this cwd/relative-path sensitivity, not a real recursion-related bug. Keep cwd fixed when comparing the two modes. This cwd='.' sensitivity is also the source of the leading-'./' bug fixed in R11.

### R6 — No literal upstream fix commit is retrievable from this checkout

This local clone's history stops at/near the base commit (7543 commits, tags only up to v2.9.x, no `main` branch with later commits). `git log --all --grep` for "7080", "separator", or further ignore-paths/recursive fixes returns nothing beyond the base. Do not expect to find the real accepted #7080 fix diff by searching this checkout's git history — any fix must be derived from reasoning + reproduction against the current code, as done in R11, not copied from a later upstream commit.

### R7 — Directory-level ignore-paths check in _discover_files is dead for anchored patterns

In pylint/lint/pylinter.py, `_discover_files` calls `_is_ignored_file(root, ...)` on the bare directory path (e.g. `src/gen`, no trailing separator). For an anchored pattern like `^src/gen/.*$`, this can never match a bare directory path (nothing after `gen`) — verified via re.match against both POSIX and Windows-normalized variants. This walk-level check is effectively dead code for this pattern shape.

For package directories, this causes no visible bug because expand_modules() has two independent later checks that compensate: (1) `_is_ignored_file` on the yielded file path itself, and (2) `_is_in_ignore_list_re(subfilepath, ...)` inside `get_module_files` for package directories (expand_modules.py ~137-146). For package-less directories neither compensating check applies — see R11.

### R8 — _discover_files skips file-level ignore check, but expand_modules re-checks it for package directories only

PyLinter._discover_files (pylint/lint/pylinter.py ~585-619, os.walk-based recursive discovery) only calls _is_ignored_file() on the directory (`root`), never on individual .py file paths it yields. For directories containing `__init__.py` this is NOT a bypass end-to-end: every yielded path flows through self.check() -> _iterate_file_descrs -> _expand_files -> expand_modules() (pylint/lint/expand_modules.py), whose main loop (~line 78-81) re-checks each file, and package-internal files recursed via modutils.get_module_files are also re-checked (~line 143-146).

This compensation does NOT hold for package-less directories (no `__init__.py` anywhere in the tree) — R11 confirms individual files yielded from those are never checked against ignore rules at all. Do not propose "add per-file _is_ignored_file check to _discover_files" as the *complete* fix without also handling the leading-'./' normalization in R11 — a per-file check alone still fails when cwd is '.'.

### R9 — Corpus/approach assigned to this topic key is actually Flask Blueprint dot-validation content (reverse contamination)

Distinct from the aspect-name contamination in [[aspect-pylint-contamination#R1]] (pylint aspects dispatched onto non-pylint topics), this is the reverse: the *approach* and *instance corpus* handed to topic key `pylint-dev__pylint-7080` (24 instances, dims `has_dot`/`name_shape`/`registration_context`) are entirely about Flask `Blueprint` name dot validation — the actual content of `pallets__flask-4045` (see [[pallets-flask-4045#X1]]) — not about this topic's real ignore-paths/`--recursive` bug described in this skill's own R1-R11.

Why: `src/flask/blueprints.py` does not exist in this pylint checkout — confirmed by direct check, not inference. Observed repeatedly across independent tune-stage runs (including one that received a `column-command-domain`/flask `routes_command` corpus instead), both failing to find any applicable code.

How to apply: if a task under this topic key hands you a Blueprint-dot-name or Flask-routes corpus/approach, discard it immediately and work from this skill's own R1-R11/X1-X3 (the real ignore-paths bug) instead of trying to force the mismatched corpus onto pylint source.

### R10 — python -m pylint can crash with ModuleNotFoundError/UnknownMessageError from a shadowing install

Running `python -m pylint` in this sandbox can raise ModuleNotFoundError or UnknownMessageError — not a real bug in this checkout's pylint/astroid, but an unrelated site-packages pylint/astroid install (or a leftover sys.path entry from a different worktree's tmp dir) shadowing the repo checkout. Before trusting a crash as evidence about #7080's code, check `python -c "import pylint; print(pylint.__file__)"` resolves to this checkout's `pylint/` and not a site-packages copy, and check sys.path for stale tmp entries from other worktrees.

### R11 — VERIFIED FIX: per-file ignore check in _discover_files + normpath on root/file strips os.walk's leading './'

CONFIRMED WORKING (upgraded from earlier conflicting/untested status — see X3). Fixing `--recursive=y` ignoring `ignore-paths` needs two independent changes together in `pylinter.py::_discover_files`, not either alone:

1. Individual files yielded from directories WITHOUT `__init__.py` were never checked against ignore rules at all — only `os.walk`'s `root` dirs were checked (R7/R8's dead-code gap does NOT get compensated for package-less directories, unlike the package case R8 describes). Fix: add a per-file `_is_ignored_file` check for every yielded file, not just the directory root.
2. `os.walk('.')` yields roots with a leading `./` (e.g. `./subdir`), which breaks anchored patterns like `^subdir/.*$` since the pattern has no `./` prefix to match. Fix: `os.path.normpath()` the root/file path before passing it to the ignore check.

Fixing only #1 without #2 still fails whenever cwd is `.` (the common case). Two independent approaches (A6, A8) converged on this identical combined fix; a third (A7) had only #1 and still failed the cwd='.' case, confirming #2 is required.

Applied live and verified: all 7 recursive/ignore-paths tests pass. The full suite's 22 pre-existing failures were confirmed pre-existing/environmental (not caused by this fix) via a git-stash baseline diff — the same 22 fail with the fix reverted.

### R12 — research_define_fom won't rename once approaches are scored, so a mislabeled FOM from R9's contamination persists

When R9's reverse contamination (Flask Blueprint dot-validation corpus/approaches handed to this topic key) reaches the FOM-definition stage before it's caught, `research_define_fom` refuses to rename the figure of merit once approaches (observed: A1, A2, A4, A9) have already been scored against it. The FOM stays permanently labeled `blueprint_dot_validation_accuracy` for this pylint task even after the mismatch is recognized — there is no in-place rename/recovery path.

How to apply: don't spend time retrying `research_define_fom` to fix the label after scoring has started. Instead work around it — adopt a still-valid approach (e.g. A6, the R11-verified fix) as the nominal one rather than trying to force a rename or re-score. Catching R9's contamination *before* the first `research_define_fom`/scoring call is the only way to avoid this; once approaches are scored, the mislabel is permanent for that run.

## References

### X1 — Two prior ignore-paths/recursive fixes are already present at base commit

Two commits that look like plausible fixes for #7080 are already merged into this checkout and do NOT reproduce the bug when tested:
1. bfc8d322 (PR #5201, closes #5194) — dual-compiles ignore-paths regex for both Windows (`\\`) and POSIX (`/`) separators via `_regexp_paths_csv_validator`/`_regexp_paths_csv_transfomer` in pylint/config/option.py and pylint/config/argument.py.
2. 9c2fe999 / 6ad350fb (PR #6528) — added `_is_ignored_file()` (pylint/lint/expand_modules.py) and wired it into `PyLinter._discover_files` (pylint/lint/pylinter.py) so `--recursive=y` consults ignore/ignore-patterns/ignore-paths during os.walk.
Both were reproduced as already-working via a minimal repro (src/main.py + src/gen/about.py + pyproject.toml `[tool.pylint.MASTER] ignore-paths = ["^src/gen/.*$"]`, run with `pylint.lint.Run(['--recursive=y','src/'])`), tested with and without `src/gen/__init__.py`. In both cases `src/gen/about.py` was correctly excluded — this is the package-directory case. Do not re-propose these as a complete fix for #7080 — see R11 for the package-less-directory gap they don't cover.

### X2 — Evidence: flat-root nested-ignored-file scenario already works on unmodified code

Empirical repro (tmp/research/repro2/: good.py at top level, sub/bad_ignored.py nested, sub/ containing __init__.py) run with `--recursive=y` plus each of --ignore, --ignore-patterns, --ignore-paths on unmodified pylint 2.15.0-dev0 checkout: sub/bad_ignored.py correctly excluded in all cases. This is the package-directory case; tests/lint/unittest_lint.py::test_recursive_ignore covers the identical shape and passes on unmodified code for the same reason.

This investigation did not cover a genuinely package-less directory (no `__init__.py` anywhere) as the ignored subtree — that shape IS buggy on unmodified code; see R11 for the confirmed fix.

### X3 — Package-less-directory case confirmed buggy and fixed — see R11

An earlier session reported a conflict between R8's package-case refutation and a claim that _discover_files' directory-only ignore check causes --recursive=y to ignore ignore-paths. That conflict is now resolved: the package-less-directory shape X2 left untested IS genuinely buggy on unmodified code, and R11 records the verified two-part fix (per-file check + normpath for the leading './' case), applied live with all 7 recursive/ignore tests passing.
