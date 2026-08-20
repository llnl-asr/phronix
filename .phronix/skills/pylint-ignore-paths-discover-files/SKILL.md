---
name: pylint-ignore-paths-discover-files
description: The pylint-ignore-paths-discover-files subject.
subject: pylint-ignore-paths-discover-files
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Minimal repro for the _discover_files package-dir bug |
| `R1` | Rules | Must use --recursive=y to exercise _discover_files |
| `R2` | Rules | Bug only user-visible for package dirs, not loose .py files |
| `R3` | Rules | Two separate import bindings of _is_ignored_file — patch both when tracing |





## Instructions

### I1 — Minimal repro for the _discover_files package-dir bug

```
mkdir -p src/gen; echo 'print(undefined_variable)' > src/gen/__init__.py
python -c "from pylint.lint.run import Run; Run(['--recursive=y',
  '--ignore-paths=^src/gen/.*$','--disable=all','--enable=undefined-variable','src'])"
```
Use `undefined-variable` as the marker, not `unused-import` — pylint doesn't flag unused-import in `__init__.py` by default regardless of ignoring, which is a red herring that looks like "no bug" for the wrong reason.

## Rules

### R1 — Must use --recursive=y to exercise _discover_files

`PyLinter._discover_files` (pylint/lint/pylinter.py ~line 585) only runs when `--recursive=y` is set (pylinter.py line 634: `if self.config.recursive: files_or_modules = tuple(self._discover_files(...))`). Testing an ignore-paths anchoring fix without `--recursive=y` gives a false "no bug" result because the function is skipped entirely.

### R2 — Bug only user-visible for package dirs, not loose .py files

The `_discover_files` anchoring bug (`_is_ignored_file(root,...)` failing on `^src/gen/.*$` because `os.walk`'s root has no trailing separator) is masked for loose `.py` files with no `__init__.py`: `expand_modules()` independently re-checks the full joined file path (e.g. `src/gen/foo.py`), which already has content after the `/` and matches correctly. It is only user-visible for package directories (dir containing `__init__.py`), where `_discover_files` does `yield root` — the bare dir string — as the module to lint, and no downstream check saves it. To reproduce the real symptom, test with a package dir, not loose files.

### R3 — Two separate import bindings of _is_ignored_file — patch both when tracing

`_is_ignored_file` is referenced via two separate bindings: `pylint.lint.pylinter._is_ignored_file` and `pylint.lint.expand_modules._is_ignored_file` (imported via `from pylint.lint.expand_modules import _is_ignored_file`). When monkeypatching for tracing/debugging, patch the binding actually referenced in each module's global namespace — `from X import Y` creates an independent reference, so patching only the origin module misses calls made through the other.

## References
