---
name: pylint-ignore-paths-recursive
description: The pylint-ignore-paths-recursive subject.
subject: pylint-ignore-paths-recursive
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix location: normalize path before _is_ignored_file, not add more call sites |


## Instructions

### I1 — Fix location: normalize path before _is_ignored_file, not add more call sites

Bug: `pylint --recursive=y ignore-paths=...` fails to ignore files when pylint is invoked with `.` as the target (e.g. `pylint --recursive=y .` from inside the target dir).

Root cause (confirmed by walking `os.walk(".")` and inspecting `_is_ignored_file`): `os.walk(".")` yields root/file paths prefixed with the literal `./` (e.g. `./ignored_subdirectory/failing.py`). `_is_in_ignore_list_re` in pylint/lint/expand_modules.py does `re.match` (anchored at index 0, not full match, no normalization). An `--ignore-paths` pattern that isn't itself prefixed with a wildcard (e.g. `ignored_subdirectory/.*` rather than `.*ignored.*`) never matches a path starting with `./`.

Correct fix: in `pylinter.py::_discover_files`, normalize `root` (e.g. `os.path.normpath(root)`, or strip the `./` seed artifact) BEFORE passing it to `_is_ignored_file` — for both the existing directory-level check and any file-level check. Do not modify `_is_ignored_file`/`_is_in_ignore_list_re` itself in expand_modules.py — it's shared with other call sites that already pass clean paths.

Exclusion: simply adding a file-level `_is_ignored_file(os.path.join(root, file), ...)` call (mirroring the existing root-level check) does NOT fix this — one attempt tried exactly that and the target test still failed, because the bug is in the path *format* fed to the regex, not in which paths get checked.

## Rules

## References
