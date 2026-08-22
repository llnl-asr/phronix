---
name: solution-pylint-dev-pylint-7080-path-normalization-in-discover-files
description: The solution-pylint-dev-pylint-7080-path-normalization-in-discover-files subject.
subject: solution-pylint-dev-pylint-7080-path-normalization-in-discover-files
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Normalize the path inside _is_ignored_file before matching |
| `I2` | Instructions | Verify the fix |
| `R1` | Rules | Root cause is inside _is_ignored_file, not _discover_files |




## Instructions

### I1 — Normalize the path inside _is_ignored_file before matching

Edit `pylint/lint/expand_modules.py`. In `_is_ignored_file(element, ignore_list, ignore_list_re, ignore_list_paths_re)`, insert one line as the first statement of the function body, before `basename = os.path.basename(element)`:

```python
    element = os.path.normpath(element)
```

Result:

```python
def _is_ignored_file(
    element: str,
    ignore_list: list[str],
    ignore_list_re: list[Pattern[str]],
    ignore_list_paths_re: list[Pattern[str]],
) -> bool:
    element = os.path.normpath(element)
    basename = os.path.basename(element)
    return (
        basename in ignore_list
        or _is_in_ignore_list_re(basename, ignore_list_re)
        or _is_in_ignore_list_re(element, ignore_list_paths_re)
    )
```

`os.path` is already imported at the top of the file; no new import needed. Do not edit `pylint/lint/pylinter.py`.

### I2 — Verify the fix

Run `python -m pytest tests/test_self.py -k test_ignore_path_recursive_current_dir -q` from the repo root. It must pass with exit code 0 and no other tests newly broken. Also sanity-check by hand: create a dir with `ignored_subdirectory/failing.py` (containing lint errors) and a config with `ignore-paths=^ignored_subdirectory/.*$`, then run `python -m pylint --recursive=y .` from inside that dir — expect a clean run (exit 0, no messages), whereas before the fix it reports `failing.py` errors.

## Rules

### R1 — Root cause is inside _is_ignored_file, not _discover_files

`_discover_files` in `pylint/lint/pylinter.py` already calls `_is_ignored_file(root, ...)` correctly for every directory root from `os.walk`, and yields `.py` files under a root only when that root passed the check — so a matched root already suppresses its files. The bug is that `os.walk(".")` yields roots like `./ignored_subdirectory`, and `_is_ignored_file` matches that raw string against anchored regexes such as `^ignored_subdirectory/.*$`, which never matches because of the leading `./`. Fix the mismatch where it originates — inside `_is_ignored_file` — by normalizing before comparing. Do not add a second, redundant ignore check per-file in `pylinter.py`; that was already tried and failed.

## References
