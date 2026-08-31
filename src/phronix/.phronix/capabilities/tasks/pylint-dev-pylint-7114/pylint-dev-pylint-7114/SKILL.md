---
name: pylint-dev-pylint-7114
description: The pylint-dev-pylint-7114 subject.
subject: pylint-dev-pylint-7114
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | What problem it solves |
| `I3` | Instructions | The key idea |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | Constraints and rules |
| `I6` | Instructions | Lessons |

## Instructions

### I1 — Problem description

Running pylint on a package where a module has the same name as its containing package fails because pylint expects an __init__.py file. The test `test_identically_named_nested_module` fails with a missing `deprecated-module` message.

### I2 — What problem it solves

Running `pylint a` fails with a parse error when `a/a.py` exists but `a/__init__.py` doesn't exist. The issue occurs because pylint's module resolution in `get_python_path()` (expand_modules.py) still checks for `__init__.py` existence, which is not required since Python 3.3 for namespace packages. When a user runs `pylint a` intending to lint module `a`, pylint incorrectly reports `E0611: No name '...' in module 'a'` and `F0010: error while code parsing: Unable to load file a/__init__.py: [Errno 2] No such file or directory` even though the module `a.py` exists and is valid Python code.

### I3 — The key idea

The key insight is: `the email field is not always called email` (adapted for this context). In pylint module resolution, the `get_python_path()` function incorrectly assumes every module directory needs an `__init__.py` file, but since Python 3.3, directories can be packages (namespace packages) without `__init__.py`. The fix is to remove the `__init__.py` check from `get_python_path()` so that directories without `__init__.py` are treated as valid module paths.

### I4 — Instructions to solve it

1. Edit `pylint/lint/expand_modules.py` - modify the `get_python_path()` function to remove the `__init__.py` existence check.
2. The current function (lines 26-41) walks up directories checking for `__init__.py` at each level. Remove this check entirely.
3. Replace the function body to simply return the directory name as the Python path, without checking for `__init__.py`.
4. This allows directories without `__init__.py` to be treated as valid module paths, consistent with Python 3.3+ behavior where namespace packages don't require `__init__.py`.
5. After the change, run the test case: create a directory `a/` with `a/a.py` but without `a/__init__.py`, then run `pylint a` - it should succeed without F0010 or E0611 errors.

### I5 — Constraints and rules

1. Do NOT modify any test files - the fix must work with existing tests.
2. The change must only affect module resolution for directories without `__init__.py`; directories with `__init__.py` should continue to work as before.
3. Do NOT change the `expand_modules()` function logic beyond the `get_python_path()` modification.
4. The fix must be minimal - only remove the `__init__.py` check from `get_python_path()`, do not restructure the entire module resolution.
5. After the fix, `pylint a` must pass when `a/a.py` exists but `a/__init__.py` does not, without introducing regressions for normal packages with `__init__.py`.
6. The existing test suite for module expansion must still pass - do not cause any previously passing tests to fail.

### I6 — Lessons

1. The get_python_path() __init__.py check is the single point of failure - removing it fixes the issue without breaking existing functionality.
2. Python 3.3+ supports namespace packages without __init__.py, and pylint's code was not updated to reflect this.
3. Timing variance (12 min vs 2 min) reflects difficulty locating this issue without knowing where to look - get_python_path() is the key place.
4. Following skill rules about not modifying test files is critical for a lasting fix.

## References
