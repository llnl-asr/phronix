---
name: pylint-dev-pylint-5859
description: The pylint-dev-pylint-5859 subject.
subject: pylint-dev-pylint-5859
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Do not add separator-normalization code for this fix |
| `R2` | Rules | Aspect brief mismatch: ignore this task's non_recursive_reference_behavior framing |
| `R3` | Rules | The real issue is a --notes punctuation-tag bug, not discovery/ignore-paths |
| `R4` | Rules | _discover_files does no ignore-paths filtering; enforcement is downstream |
| `R5` | Rules | Aspect brief mismatch: this task's real FoM is fixme_note_tag_detection_rate, not ignore-paths |
| `X1` | References | Actual bug location: fixme regex in misc.py |
| `X2` | References | Discovery/expand_modules flow in this codebase version (base commit 182cc539b815) |
| `X3` | References | Config dest-name gotchas for ignore-related options (from unrelated but verified investigation) |









## Instructions

## Rules

### R1 — Do not add separator-normalization code for this fix

expand_modules.py applies os.path.normpath only to the top-level isarg=True filepath, never to subfilepath from the recursive os.walk-based get_module_files. This is a real latent issue for Windows (os.walk yields backslashes there, ignore-paths patterns are conventionally forward-slash), but the actual reported bug reproduces on Linux too (os.sep=='/'), so it is a separate "scope of check" bug (ignore-paths not applied consistently to every recursively-discovered file), not a separator bug. Because this repo's test suite runs on Linux, any separator-normalization change (e.g. subfilepath.replace(os.sep,'/')) is unverifiable here and risks masking whether the real scope-bug fix works. Do not include separator normalization in the fix or its tests; keep the fix scoped to applying _is_in_ignore_list_re consistently during the recursive walk. See research approach "normalize-subfilepath-separators" (refuted) under aspect windows_path_separator_interaction.

### R2 — Aspect brief mismatch: ignore this task's non_recursive_reference_behavior framing

The aspect "non_recursive_reference_behavior" as briefed (expand_modules() vs. recursive _discover_files ignore-paths handling in pylint/lint/expand_modules.py and pylinter.py) does not match this task's actual bug. This task's issue.md is about `--notes` ignoring note tags that are entirely punctuation (e.g. `pylint test.py --notes="???"` doesn't flag `# ???: no`). That brief appears copied from a different, unrelated pylint issue (likely an ignore-paths-not-applied-recursively bug, possibly pylint-dev/pylint #5901). Do not re-investigate expand_modules/ignore-paths for this task — see [[fix-fixme-regex-word-boundary]] approach for the real fix location.

### R3 — The real issue is a --notes punctuation-tag bug, not discovery/ignore-paths

The actual GitHub issue for pylint-dev/pylint#5859 is "--notes option ignores note tags that are entirely punctuation" (e.g. `pylint test.py --notes="YES,???"` fails to flag `???` as W0511 fixme). This is a fixme/notes-tag regex bug, likely in pylint/checkers/base.py's note-tag pattern construction (possibly a \b word-boundary issue that doesn't match tags with no word characters), NOT a discovery/_discover_files/ignore-paths/expand_modules bug. Multiple aspect briefs in this task's research plan (discovery_ignore_check_scope, and sibling dirs seen: aspect-root-path-regex-mismatch, aspect-non-recursive-reference-behavior, aspect-upstream-fix-reference) describe an ignore-paths investigation that does not match the actual issue text — likely cross-talk from a different task's aspect set. Any implementation work should target the notes/fixme checker matching the issue text, not pylint/lint/pylinter.py or expand_modules.py.

### R4 — _discover_files does no ignore-paths filtering; enforcement is downstream

`PyLinter._discover_files` (pylint/lint/pylinter.py, os.walk-based, ~line 1016) never calls `_is_in_ignore_list_re` and never references `ignore_list_paths_re`/`self._ignore_paths` — it yields all files/dirs unfiltered. Enforcement happens later in `expand_modules()` (pylint/lint/expand_modules.py) via `_is_in_ignore_list_re(something, ignore_list_paths_re)` against full paths (each item from files_or_modules, and each subfilepath from `modutils.get_module_files` for package expansion) — never against bare os.walk roots.

Do not build a fix around "match the bare os.walk root against ignore-paths regex with a trailing slash added" — no confirmed call site does that today. See [[pylint-dev__pylint-5859#lesson-root-regex-mismatch-not-reproduced]] for why the isolated regex-anchoring bug doesn't manifest as a real leak.

### R5 — Aspect brief mismatch: this task's real FoM is fixme_note_tag_detection_rate, not ignore-paths

This topic's actual figure-of-merit (confirmed via research_add_approach / research_coverage) is `fixme_note_tag_detection_rate`, dimensions `should_match`, `tag_char_class`, `tag_position`, `trailing_context` — the W0511 fixme-checker's TODO/FIXME comment-tag regex matching. It is NOT about file discovery, `--recursive`, or `--ignore-paths`, despite an aspect brief for this task pointing at pylinter.py `_discover_files`.

Why: the brief appears confused with a different, superficially similar issue (overlapping search terms "ignore-paths"/"recursive"). No `issue.md` was available to confirm the real issue text.

How to apply: before building on the `_discover_files`/ignore-paths findings under this topic (approaches A1, A8, A9), re-check `research_coverage` for the real FoM. Any final patch should target the fixme-checker regex, not `pylinter.py`/`expand_modules.py`.

## References

### X1 — Actual bug location: fixme regex in misc.py

The real bug for this task is in pylint/checkers/misc.py, EncodingChecker, around lines 118-128, where `self._fixme_pattern` is built as `rf"#\s*({notes})\b"` (or with notes_rgx). The trailing `\b` word-boundary fails to match when a note tag is entirely punctuation. See approach [[fix-fixme-regex-word-boundary]] for the confirmed repro and fix direction.

### X2 — Discovery/expand_modules flow in this codebase version (base commit 182cc539b815)

`_is_ignored_file` does not exist anywhere in pylint/lint/pylinter.py or pylint/lint/expand_modules.py at base commit 182cc539b815 — grepped and confirmed absent. Discovery flow: PyLinter.check() → if --recursive: files_or_modules replaced with list(_discover_files(...)) (no ignore filtering at this stage, and it already flattens to file-level or single-package-root granularity, never a whole non-package directory tree in one blob) → _iterate_file_descrs → _expand_files → expand_modules(modules, ignore_list, ignore_list_re, ignore_list_paths_re). expand_modules (pylint/lint/expand_modules.py:53-60) loops over every flattened item and checks basename against --ignore, basename against --ignore-patterns, and full path against --ignore-paths, before processing further. This is relevant background if a future aspect on this task genuinely needs discovery/ignore-paths behavior — but see [[pylint-dev__pylint-5859#R1]] first: the actual issue for this task is unrelated to discovery/ignore-paths.

### X3 — Config dest-name gotchas for ignore-related options (from unrelated but verified investigation)

If ignore-paths/recursive-discovery code is ever touched in this repo (pylint/lint/pylinter.py, pylint/lint/expand_modules.py), note the actual attribute names on `self.config`, which don't match the CLI flag names:
- `--ignore` → `self.config.black_list` (not `self.config.ignore`)
- `--ignore-patterns` → `self.config.black_list_re` (not `self.config.ignore_patterns`)
- `--ignore-paths` → `self.config.ignore_paths` (keeps its natural name; no custom `dest` in `make_options()`)
- `pylint/lint/expand_modules.py::_is_in_ignore_list_re(element, ignore_list_re)` is the existing reusable basename-or-fullpath regex-match helper — reuse it rather than reimplementing.
- `expand_modules.py` (lines ~53-59 and ~122-125) already re-checks `ignore_list_paths_re` against every file/subfile discovered by `_discover_files`, via `PyLinter._iterate_file_descrs` → `_expand_files`. So a bug isolated by calling `_discover_files` alone (without running the full `check()` pipeline) can look worse than it is in end-to-end behavior — always retest through the full pipeline before concluding a discovery-time filter is missing.
