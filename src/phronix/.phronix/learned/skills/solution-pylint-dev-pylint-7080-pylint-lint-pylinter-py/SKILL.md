---
name: solution-pylint-dev-pylint-7080-pylint-lint-pylinter-py
description: The solution-pylint-dev-pylint-7080-pylint-lint-pylinter-py subject.
subject: solution-pylint-dev-pylint-7080-pylint-lint-pylinter-py
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Root cause: unnormalized os.walk root breaks anchored ignore-paths regex |
| `I2` | Instructions | Fix: normalize element with pathlib.Path in _is_ignored_file |
| `I3` | Instructions | Check: reproduce the recursive-current-dir ignore-paths scenario |




## Instructions

### I1 — Root cause: unnormalized os.walk root breaks anchored ignore-paths regex

`PyLinter._discover_files` (pylint/lint/pylinter.py ~line 595) calls `os.walk(something)`. When invoked as `pylint --recursive=y .`, `something` is `"."`, so `os.walk` yields roots like `./ignored_subdirectory` (leading `./` kept). This root is passed into `_is_ignored_file` (pylint/lint/expand_modules.py), which `re.match`s it against the compiled `ignore-paths` regexes (e.g. `^ignored_subdirectory/.*$`). Because the string still starts with `./`, the anchored regex never matches, so `ignore-paths` is silently ignored for `.`-relative recursive runs — exactly the bug in the issue.

### I2 — Fix: normalize element with pathlib.Path in _is_ignored_file

In `pylint/lint/expand_modules.py`, edit `_is_ignored_file` (~line 49-60) to normalize the incoming path via `pathlib.Path` before matching, so `str(Path('./ignored_subdirectory'))` becomes `'ignored_subdirectory'` (leading `./` stripped) and the anchored `ignore-paths` regex matches again:

```python
from pathlib import Path  # add to imports if missing

def _is_ignored_file(
    element: str,
    ignore_list: list[str],
    ignore_list_re: list[Pattern[str]],
    ignore_list_paths_re: list[Pattern[str]],
) -> bool:
    element = Path(element)
    basename = element.name
    return (
        basename in ignore_list
        or _is_in_ignore_list_re(basename, ignore_list_re)
        or _is_in_ignore_list_re(str(element), ignore_list_paths_re)
    )
```

No call-site changes needed: `pylinter.py`'s `_discover_files` passes `root` from `os.walk`, and `expand_modules`'s own call passes a file path — both are normalized by this one change.

### I3 — Check: reproduce the recursive-current-dir ignore-paths scenario

Build a temp tree containing `ignored_subdirectory/failing.py` (with lint violations) plus a pyproject.toml/pylintrc with `ignore-paths = ["^ignored_subdirectory/.*$"]`. `cd` into that temp dir and run, from the repo checkout: `python -m pylint --recursive=y .`.

Before the fix: reports messages for `failing.py` and exits 20.
After the fix: reports nothing under `ignored_subdirectory`, exits 0.

Also verify files outside `ignored_subdirectory` are still linted normally (non-empty output for those), to confirm the change didn't over-ignore everything.

## Rules

## References
