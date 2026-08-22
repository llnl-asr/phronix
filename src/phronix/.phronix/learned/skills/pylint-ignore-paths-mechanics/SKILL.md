---
name: pylint-ignore-paths-mechanics
description: How pylint's ignore-paths CLI option is registered, transformed, and matched — for pylint-dev__pylint-7080 style bugs.
subject: pylint-ignore-paths-mechanics
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Open threads not yet verified — what to check next |
| `R1` | Rules | ignore-list regex matching uses re.match, not re.search, for both option types |
| `X1` | References | ignore-paths option type: regexp_paths_csv transformer |




## Instructions

### I1 — Open threads not yet verified — what to check next

Not yet confirmed by this investigation (regex_option_type_semantics aspect); worth checking before relying on the re.match/relative-path theory:
1. Whether astroid's `modutils.get_module_files` (used by `expand_modules()` for the `subfilepath` passed to `_is_in_ignore_list_re`) returns relative or absolute paths — assumed similar to `_discover_files`'s `root` but not directly read from astroid source.
2. Whether any earlier layer (pylint/lint/run.py or `Run.__init__`) normalizes `files_or_modules` to absolute paths before it reaches `_discover_files` — if it does, the relative/absolute inconsistency theory needs revisiting.
3. Whether plain-string `ignore` (non-regex) has an analogous relative/absolute inconsistency — out of scope for this aspect, not checked.
4. The actual pylint-7080 issue text was not read in this pass — the re.match/relative-path theory is plausible from code reading alone but not confirmed against the reported symptom.

## Rules

### R1 — ignore-list regex matching uses re.match, not re.search, for both option types

`_is_in_ignore_list_re` (pylint/lint/expand_modules.py:44-46) does `any(p.match(element) for p in ignore_list_re)` — `.match()` anchors at the START only, so it's a prefix match, not a substring search. Reused identically for `ignore-patterns` (vs basename) and `ignore-paths` (vs full walked path).

Why: the path matched is `os.walk`'s `root` in `_discover_files`, never passed through `os.path.abspath()`, so its relative/absolute form depends on the CLI arg. A pattern meant to match "anywhere" (e.g. `tests/`) needs a leading `.*` (e.g. `.*/tests/.*`) to behave like a search.

How to apply: when `ignore-paths` "doesn't ignore" a nested path, check for missing leading `.*` and relative/absolute mismatch first — do NOT blame the `regexp_paths_csv` type registration, it doesn't affect anchoring (see [[pylint-ignore-paths-mechanics#X1]]).

## References

### X1 — ignore-paths option type: regexp_paths_csv transformer

`ignore-paths` is registered with `"type": "regexp_paths_csv"` in pylint/lint/base_options.py (~line 65-73), distinct from `ignore-patterns`'s `"type": "regexp_csv"`.

`_regexp_paths_csv_transfomer` (pylint/config/argument.py:110-121) compiles, for each comma-separated user pattern, a single regex that is the OR of:
- the pattern run through `pathlib.PureWindowsPath(...)` then stringified with `\` escaped to `\\` (backslash-separator form)
- the same `PureWindowsPath(...).as_posix()` form (forward-slash-separator form)

This only duplicates path-separator handling so a pattern like `foo/bar` also matches `foo\bar` cross-platform. It does NOT add anchors (`^`/`$`) and does NOT change any other regex semantics of the user's pattern. Contrast with `_regexp_csv_transfomer` (used for `ignore-patterns`) which just `re.compile`s each pattern verbatim after CSV splitting.

`_TYPE_TRANSFORMERS` dict (pylint/config/argument.py:134-135) maps `"regexp_paths_csv"` -> `_regexp_paths_csv_transfomer`, `"regexp_csv"` -> `_regexp_csv_transfomer`.
