---
name: solution-pylint-dev-pylint-7080-skip-subtrees-prefix-matching-bug
description: The solution-pylint-dev-pylint-7080-skip-subtrees-prefix-matching-bug subject.
subject: solution-pylint-dev-pylint-7080-skip-subtrees-prefix-matching-bug
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Edit: normalize root at the top of the os.walk loop |
| `I2` | Instructions | Check: verify the fix against a reproduction directory |
| `R1` | Rules | Why this fixes the startswith prefix bug and not just the regex |




## Instructions

### I1 — Edit: normalize root at the top of the os.walk loop

In `pylint/lint/pylinter.py`, method `_discover_files`, find:

```python
for root, _, files in os.walk(something):
    if any(root.startswith(s) for s in skip_subtrees):
```

Insert a normalization line immediately after unpacking `root`, before it is used anywhere:

```python
for root, _, files in os.walk(something):
    root = os.path.normpath(root)
    if any(root.startswith(s) for s in skip_subtrees):
```

Do not edit `pylint/lint/expand_modules.py` (`_is_ignored_file`, `_is_in_ignore_list_re`) — they are correct once given an already-normalized path.

### I2 — Check: verify the fix against a reproduction directory

Create a temp dir `pkg/ignored_subdirectory/mod.py` (with a lint violation) and `pkg/other/mod.py` (with a lint violation), plus a `pylintrc` or `pyproject.toml` in `pkg` setting `ignore-paths` to `^ignored_subdirectory/.*$` (pylintrc: `ignore-paths=ignored_subdirectory/.*`). From inside `pkg`, run `python -m pylint --recursive=y .` using this repo's checkout (not a globally installed pylint).

Before the fix: messages are still emitted for files under `ignored_subdirectory` (regex never matched `./ignored_subdirectory`).

After the fix: no messages/exit code reflects only `other/mod.py`'s violation — `ignored_subdirectory` produces nothing, while `other` is still linted normally.

## Rules

### R1 — Why this fixes the startswith prefix bug and not just the regex

`root` comes raw from `os.walk`, so it can be `./ignored_subdirectory` when walking `"."`. `_is_ignored_file` matches `root` against `ignore_paths` regexes with `Pattern.match`, so an anchored pattern like `^ignored_subdirectory/.*$` never matches the `./`-prefixed form — the ignore is silently skipped.

Rebinding `root = os.path.normpath(root)` once, before any use in the loop body, means every later reference — the `skip_subtrees` membership check, the `_is_ignored_file` call, `skip_subtrees.append(root)`, and the `yield`/`os.path.join` calls — all use the same normalized value. There is no separate "call site" vs. "storage" form to keep in sync, so the `any(root.startswith(s) for s in skip_subtrees)` check stays consistent by construction. Normalizing in only one of those spots (e.g. only inside the `_is_ignored_file` call, or only when appending) would reintroduce a normalized-vs-unnormalized mismatch — normalize once, into the loop variable itself, not at individual call sites.

## References
