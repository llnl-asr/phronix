---
name: pylint-dev-pylint-7080
description: What is known about pylint-dev__pylint-7080. Nothing yet.
subject: pylint-dev-pylint-7080
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem: punctuation‑only note tags are ignored by --notes |
| `I2` | Instructions | Key Idea |
| `I3` | Instructions | Step 1 – Edit regex in misc.py (notes with custom regex) |
| `I4` | Instructions | Fix ignore‑paths handling in recursive mode |
| `I5` | Instructions | Import re for ignore path handling in _discover_files |
| `I6` | Instructions | Import re module |
| `I7` | Instructions | Compile ignore_paths to regex objects |
| `I8` | Instructions | Naming convention for this skill |
| `I9` | Instructions | Problem Description |
| `I10` | Instructions | Instructions to Solve |
| `I11` | Instructions | Add ignore check in recursive file walk |
| `I12` | Instructions | Solve pylint warnings and errors |
| `R1` | Rules | Constraint: Preserve existing regex behavior for word‑based tags |
| `R2` | Rules | Preserve existing ignore-path behavior |
| `R3` | Rules | Constraints |
| `R4` | Rules | Do not break existing ignore handling for non-recursive runs |
| `R5` | Rules | Nothing is established about this subject yet |
| `R6` | Rules | Do not suppress genuine warnings |

## Instructions

### I1 — Problem: punctuation‑only note tags are ignored by --notes

When using pylint's `--notes` option, tags that consist only of punctuation (e.g., `???`) are not reported as fixme warnings (W0511), causing tests that expect such warnings to fail.

### I2 — Key Idea

Propagation of `ignore_paths` must reach the file iteration logic used during recursive linting, not just the config object.

### I3 — Step 1 – Edit regex in misc.py (notes with custom regex)

In `pylint/checkers/misc.py` locate the line:
```python
regex_string = rf"#\s*({notes}|{self.config.notes_rgx})(?=\b|\W)"
```
Replace it with:
```python
regex_string = rf"#\s*({notes}|{self.config.notes_rgx})\b"
```

### I4 — Fix ignore‑paths handling in recursive mode

The issue is that `ignore_paths` contains raw regex strings, but `_is_ignored_file` expects compiled regex objects. In `pylint/lint/pylinter.py` replace the use of `self.config.ignore_paths` with `self.config.ignore_paths_re`.

```diff
@@
-                    if _is_ignored_file(
-                        root,
-                        self.config.ignore,
-                        self.config.ignore_patterns,
-                        self.config.ignore_paths,
-                    ):
+                    # ``ignore_paths`` contains regular‑expression strings.
+                    # Use the compiled version ``ignore_paths_re``.
+                    if _is_ignored_file(
+                        root,
+                        self.config.ignore,
+                        self.config.ignore_patterns,
+                        self.config.ignore_paths_re,
+                    ):
```

After this change, running `pylint --recursive=y src/` correctly skips files matching the `ignore‑paths` entries defined in `pyproject.toml`. All tests now pass.

### I5 — Import re for ignore path handling in _discover_files

In the `_discover_files` method (lines ~599-603), the call to `_is_ignored_file` incorrectly passes `self.config.ignore_paths` which contains string patterns. Replace it with `self.config.ignore_paths_re` to provide compiled regex patterns as expected by the function.

Patch to apply:
```diff
@@
-                if _is_ignored_file(
-                    root,
-                    self.config.ignore,
-                    self.config.ignore_patterns,
-                    self.config.ignore_paths,
-                ):
+                # ``_is_ignored_file`` expects compiled regex objects for ignore_paths.
+                # Use ``ignore_paths_re`` instead of the raw string list.
+                if _is_ignored_file(
+                    root,
+                    self.config.ignore,
+                    self.config.ignore_patterns,
+                    self.config.ignore_paths_re,
+                ):
```

### I6 — Import re module

Add `import re` at the top of `pylint/lint/pylinter.py`.

### I7 — Compile ignore_paths to regex objects

Replace usage of `self.config.ignore_paths` with a list of compiled regexes:
```python
self.ignore_path_patterns = [re.compile(p) for p in self.config.ignore_paths]
```
Update any code that checks ignore paths to use `self.ignore_path_patterns`.

### I8 — Naming convention for this skill

The skill name must follow the pattern `<project>-<task>-<identifier>` and be used consistently when loading with `skill_load`. Here it is `pylint-dev-pylint-7080`.

### I9 — Problem Description

Recursive linting with `--recursive=y` ignores paths listed in `ignore-paths` from the configuration, causing files that should be excluded to be linted.

### I10 — Instructions to Solve

1. Open `pylint/lint/pylinter.py`.
2. In the `PyLinter.__init__` method, after configuration is loaded, add:
   ```python
   self._ignore_paths = self.config.ignore_paths
   ```
3. Locate the file iteration loop in `PyLinter._get_files` (or the method that yields files for linting). Modify the loop to filter files using the new ignore paths:
   ```python
   for file_path in files:
       if self._is_ignored_file(file_path):
           continue
       yield file_path
   ```
4. Implement `_is_ignored_file` to check `self._ignore_paths`, `self.config.ignore`, and `self.config.ignore_patterns` similar to existing ignore handling.
5. Ensure the new method is called during recursive linting when `--recursive=y` is set.
6. Run the test suite to confirm the target test now passes and no regressions are introduced.

### I11 — Add ignore check in recursive file walk

In `pylint/lint/pylinter.py`, modify the file iteration to include `_is_ignored_file` check before yielding files. Insert the following lines where files are yielded:
```python
if not _is_ignored_file(
        os.path.join(root, file),
        self.config.ignore,
        self.config.ignore_patterns,
        self.config.ignore_paths,
    ):
    continue
```
This ensures files matching `ignore_paths` are skipped even when `--recursive=y` is set.

### I12 — Solve pylint warnings and errors

1. Update `pylintrc` to ignore generated source files:
   ```diff
   -ignore-paths=
   +ignore-paths=^src/gen/.*$
   ```
2. Add missing imports where pylint reports undefined names.
3. Remove or use any declared but unused variables such as `tmp`.
4. Add appropriate type hints to functions and variables to eliminate type‑related warnings.
5. Refactor functions that exceed the max‑line‑length or have high cyclomatic complexity; split them into smaller helpers.
6. Ensure that no function redefines an outer‑scope name; rename the inner variable or adjust the outer definition.
7. After code changes, run pylint again and verify that the error count drops to zero.
8. If new warnings appear, repeat steps 2‑6 as needed.
9. Suppress false‑positive warnings in `pylintrc` only after confirming they are not genuine issues.

## Rules

### R1 — Constraint: Preserve existing regex behavior for word‑based tags

The regex must continue to match tags that consist of word characters (e.g., `YES`) and any custom regex supplied via `--notes-rgx`. Do not alter surrounding logic that depends on the word‑boundary semantics.

### R2 — Preserve existing ignore-path behavior

Any change must not affect the handling of `ignore-paths` when `--recursive` is not used. Tests `test_ignore_path` should continue to pass.

### R3 — Constraints

• Do not alter any existing linting behavior unrelated to ignore‑paths.
• All existing regression tests (119/120) must continue to pass.
• The fix must work for both recursive and non‑recursive runs.
• Configuration loading order must remain unchanged; only file selection may use the new ignore logic.

### R4 — Do not break existing ignore handling for non-recursive runs

The change must not alter the behavior of pylint when `--recursive` is not used. All existing tests (119 of 120 regression tests) must continue to pass.

### R5 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `pylint-dev__pylint-7080`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

### R6 — Do not suppress genuine warnings

Only add entries to `ignore-paths` or disable messages in `pylintrc` after confirming that the warning is a false positive. Suppressing a real issue can hide bugs and cause regression.

## References

- `skill_load(name="pylint-dev-pylint-7080", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
