---
name: solution-pylint-dev-pylint-7080
description: The solution-pylint-dev-pylint-7080 subject.
subject: solution-pylint-dev-pylint-7080
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Root cause: unnormalized `./`-prefixed os.walk root breaks anchored ignore-paths regex |
| `I2` | Instructions | Fix (preferred): normalize `element` in expand_modules.py's _is_ignored_file |
| `I3` | Instructions | Alternate fix (also confirmed): normalize root in pylinter.py's os.walk loop |
| `R1` | Rules | Normalize with os.path.normpath, not pathlib.Path — the pathlib variant scored 0/target tests |





## Instructions

### I1 — Root cause: unnormalized `./`-prefixed os.walk root breaks anchored ignore-paths regex

`PyLinter._discover_files` (pylint/lint/pylinter.py) walks with `os.walk(".")` for `pylint --recursive=y .`, so `root` comes out as `./ignored_subdirectory` (leading `./` kept). That raw string is matched against anchored `ignore-paths` regexes like `^ignored_subdirectory/.*$` in `_is_ignored_file` (pylint/lint/expand_modules.py) via `Pattern.match`. Because of the leading `./`, the anchored regex never matches, so `ignore-paths` is silently ignored for `.`-relative recursive runs.

### I2 — Fix (preferred): normalize `element` in expand_modules.py's _is_ignored_file

In `pylint/lint/expand_modules.py`, as the first statement of `_is_ignored_file`, add `element = os.path.normpath(element)` before `basename = os.path.basename(element)`. `os.path` is already imported; no new import needed.

Confirmed by an independent passing trial (`tests/test_self.py::test_ignore_path_recursive_current_dir` passes, no regressions). This is the preferred fix: `_is_ignored_file` is where the anchored-regex match actually happens, and it is called both from `_discover_files`'s `os.walk` loop and from other call sites in `expand_modules.py` that pass individual file paths — normalizing here covers both, whereas normalizing only the `os.walk` root (the alternative fix) does not.

### I3 — Alternate fix (also confirmed): normalize root in pylinter.py's os.walk loop

In `pylint/lint/pylinter.py`, `_discover_files`'s `os.walk` loop: immediately after unpacking `root`, rebind `root = os.path.normpath(root)` before it is used anywhere else (the `skip_subtrees` membership check, `_is_ignored_file` call, `skip_subtrees.append`, yield/join calls).

Also confirmed by an independent passing trial. Apply only ONE of the two fixes (this or the expand_modules.py one) — both alone are sufficient; combining them is redundant with no measured benefit.

## Rules

### R1 — Normalize with os.path.normpath, not pathlib.Path — the pathlib variant scored 0/target tests

A third trial applied the same expand_modules.py location (`_is_ignored_file`) but normalized via `element = Path(element)` / `element.name` / `str(element)` instead of `os.path.normpath` + `os.path.basename`. That variant passed 0 target tests. Use `os.path.normpath`, matching the two confirmed-passing fixes, not a `pathlib.Path` rewrite of the function.

## References
