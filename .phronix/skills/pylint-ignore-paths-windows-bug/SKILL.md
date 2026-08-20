---
name: pylint-ignore-paths-windows-bug
description: The pylint-ignore-paths-windows-bug subject.
subject: pylint-ignore-paths-windows-bug
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | This bug is Windows-only; Linux cannot verify a fix end-to-end |
| `X1` | References | Bug is scoped to _is_ignored_file's path-regex branch only |



## Instructions

## Rules

### R1 — This bug is Windows-only; Linux cannot verify a fix end-to-end

The pylint-7080 bug only manifests on Windows: os.walk yields backslash paths there, which forward-slash ignore-paths regexes never match. On Linux, os.walk already yields forward-slash paths, so a Path(...).as_posix()-based fix is a no-op locally — before/after repro output is identical on Linux whether or not the fix is correct. Do not treat identical Linux before/after output as evidence the fix is wrong (or right). To positively test on Linux: monkeypatch os.walk/pathlib to simulate Windows, or test the regex-match logic directly against a manually-built backslash string using documented pathlib semantics (WindowsPath(...).as_posix() converts separators; PosixPath(...).as_posix() does not).

## References

### X1 — Bug is scoped to _is_ignored_file's path-regex branch only

In pylint/lint/expand_modules.py, _is_ignored_file(element, ignore_list, ignore_list_re, ignore_list_paths_re) has three checks: basename in ignore_list; _is_in_ignore_list_re(basename, ignore_list_re); _is_in_ignore_list_re(element, ignore_list_paths_re). Only the third ever sees a full path (not just os.path.basename), so it's the only branch that needs separator normalization — the first two operate on basenames which never contain separators on any OS. Confirmed no existing test in tests/lint/unittest_expand_modules.py constructs a Windows-style (backslash) path; all existing ignore-paths tests use posix-style patterns against real Linux paths. See related aspect aspect-discover-files-regex-anchoring-bug for a distinct, separately-investigated bug about regex anchoring vs. relative/absolute paths in the same area of code — not to be conflated with this separator issue.
