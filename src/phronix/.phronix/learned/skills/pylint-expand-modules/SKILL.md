---
name: pylint-expand-modules
description: How --recursive=y file discovery flows into ignore filtering in pylint's PyLinter
subject: pylint-expand-modules
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Recursive ignore-paths filtering already works at task base commit 3c5eca2ded3d |
| `R2` | Rules | Unexplored directions for pylint-dev__pylint-7080's remaining failure |
| `R3` | Rules | _discover_files's own root-level ignore check has a masked anchoring mismatch (not a bug worth fixing alone) |
| `X1` | References | discover_files -> expand_modules call chain (recursive ignore handling) |





## Instructions

## Rules

### R1 — Recursive ignore-paths filtering already works at task base commit 3c5eca2ded3d

Do not treat expand_modules.py/_discover_files's recursion+ignore interaction as the source of pylint-dev__pylint-7080's remaining failure. Upstream fix PR #6528 (commits 9c2fe999/6ad350fb, "Respect ignore configuration options when --recursive=y") is already an ancestor of this checkout. Empirically verified via --recursive=y --ignore-paths=... against namespace-package dirs, real-package dirs, and both "." and "src/" invocation targets: filtering is correct in all cases. `pytest tests/test_self.py -k ignore` passes (4/4) at this commit. This aspect is exhausted — look elsewhere.

### R2 — Unexplored directions for pylint-dev__pylint-7080's remaining failure

Since recursion+ignore-paths filtering is confirmed correct (see [[pylint-expand-modules#recursive-ignore-paths-already-works]]), the target test's real failure likely lies outside expand_modules.py/_discover_files. Unexplored by this aspect: (1) check_parallel / --jobs>1 code path — may skip the same ignore re-checks; (2) --ignore / --ignore-patterns specifically under recursion (only --ignore-paths was tested); (3) ignore-paths sourced from pyproject.toml/config file vs CLI flag (only CLI was tested).

### R3 — _discover_files's own root-level ignore check has a masked anchoring mismatch (not a bug worth fixing alone)

pylinter.py `_discover_files`'s own `_is_ignored_file(root, ...)` check (~line 600) tests anchored regexes (e.g. `^src/gen/.*$`) against bare os.walk `root` strings with no trailing path segment, so `.match()` can fail there. This mismatch is real but never observable as a bug: expand_modules()'s redundant checks (with os.path.normpath and full subfilepath matching) always backstop it. Confirmed masked in every scenario tried (namespace dir, real package, "." vs "src/" target). Do not "fix" this in isolation expecting it to resolve the task — it's cosmetic/redundant-check territory.

## References

### X1 — discover_files -> expand_modules call chain (recursive ignore handling)

Call chain: PyLinter.check() (pylinter.py ~621/635) calls `_discover_files()` under --recursive=y, whose output flows unfiltered into `_check_files` -> `_iterate_file_descrs` (~759) -> `_expand_files` (~767/772) -> `expand_modules(modules, ignore, ignore_patterns, ignore_paths)` (~774, expand_modules.py). expand_modules() then independently re-applies `_is_ignored_file` (basename + ignore_list_re + ignore_list_paths_re) at the top of its loop for every item, and again per-subfile via `modutils.get_module_files` (~152-159), checking both basename and full subfilepath. There is no path where a discovered file/dir reaches linting without re-passing expand_modules's own ignore checks.
