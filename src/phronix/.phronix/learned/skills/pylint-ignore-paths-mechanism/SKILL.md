---
name: pylint-ignore-paths-mechanism
description: How pylint's ignore-paths option is checked differently depending on whether files are discovered via recursive directory walk or explicit args
subject: pylint-ignore-paths-mechanism
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Check tests/lint/test_pylinter.py for existing _discover_files + ignore-paths coverage before fixing |
| `R1` | Rules | os.walk root strings have no trailing slash — anchors like /.*$ won't match them |
| `X1` | References | _discover_files vs expand_modules: two different ignore-paths code paths |




## Instructions

### I1 — Check tests/lint/test_pylinter.py for existing _discover_files + ignore-paths coverage before fixing

The investigation for [[pylint-dev__pylint-7080]] did not have time to grep tests/ exhaustively for existing ignore-paths + recursive-walk test coverage. Before implementing a fix, check tests/lint/test_pylinter.py (or wherever _discover_files is tested) for current expectations, and decide whether the fix should (a) also test full file paths per yielded file in _discover_files, (b) normalize directory paths with a trailing slash before matching, or (c) both.

## Rules

### R1 — os.walk root strings have no trailing slash — anchors like /.*$ won't match them

In pylinter._discover_files, `root` comes from os.walk and is a bare directory path with no trailing separator (e.g. "src/gen", not "src/gen/"). A regex written the natural way to ignore a directory tree, e.g. `^src/gen/.*$`, requires a literal `/` plus more content after "gen" and therefore does NOT match the bare string "src/gen" via re.Pattern.match. This causes ignore-paths regexes anchored past a trailing slash to silently fail against directory-only matching. Why: confirmed live via re.compile(r'^src/gen/.*$').match('src/gen') -> None but .match('src/gen/bad.py') -> a Match. Relevant to any pylint ignore-paths / directory-pruning bug investigation, not just [[pylint-dev__pylint-7080]].

## References

### X1 — _discover_files vs expand_modules: two different ignore-paths code paths

pylint.lint.pylinter.PyLinter._discover_files (pylinter.py:585-619, used when recursing into a directory arg without __init__.py) and pylint.lint.expand_modules.expand_modules (used for explicit/non-recursive file args, expand_modules.py:~143-145) both consult ignore-paths, but check different things: expand_modules checks ignore_list_paths_re against individual file paths; _discover_files checks _is_ignored_file only against the bare os.walk `root` directory string (never against the individual `os.path.join(root, file)` paths it yields in its else branch). A fix touching one path does not automatically fix the other — both call sites matter for [[pylint-dev__pylint-7080]].
