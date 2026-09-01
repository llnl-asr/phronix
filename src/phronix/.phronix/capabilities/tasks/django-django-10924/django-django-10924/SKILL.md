---
name: django-django-10924
description: FilePathField now accepts callable path parameter
subject: django-django-10924
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |
| `I6` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Must keep passing |
| `R2` | Rules | Must not touch |
| `R3` | Rules | Invariant |

## Instructions

### I1 — What problem it solves

When a later run arrives with a failing test involving FilePathField and a callable path, this skill helps them quickly determine if their problem matches. The symptom: user passes a callable (function, lambda) as the `path` parameter to FilePathField, and the field fails because it tries to use the callable object directly as a filesystem path instead of resolving it first.

### I2 — The key idea

The `path` parameter in `FilePathField.__init__` needs to be checked if it's callable, and if so, called to resolve the actual path string before it's used in `os.walk()` and `os.scandir()`. This is a 3-line addition that makes the field backward-compatible while adding callable support.

### I3 — Instructions to solve it

1. In `django/forms/fields.py`, find `FilePathField.__init__` method
2. Add 3 lines at the beginning of `__init__` (after the method signature, before `self.path` assignment):
   - `if callable(path): path = path()`
3. This resolves the callable to a string path before any filesystem operations
4. All existing tests must pass unchanged (backward compatibility)
5. The fix enables patterns like: `FilePathField(path=lambda: os.path.join(settings.LOCAL_FILE_DIR, 'example_dir'))`

### I4 — Constraints and rules

- Must remain backward compatible: string paths work identically to before
- Must not modify any test files
- The 3-line addition must be exactly: `if callable(path): path = path()` placed after method signature, before `self.path` assignment
- All existing field parameters (`match`, `recursive`, `allow_files`, `allow_folders`) must continue to work
- The `path` attribute must be the resolved string, not the original callable

### I5 — Pitfalls and lessons

- Earlier attempts may have tried more complex approaches (decorators, metaclasses, etc.) - these were refuted
- The simplest 3-line fix is the correct one
- Forgetting to assign the resolved path back (i.e., not assigning `path = path()`) leaves the callable unconsumed
- The fix resolves the callable at field instantiation time, not on every access - this is the expected and desired behavior

### I6 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/forms/fields.py b/django/forms/fields.py
index a977256525..6f9452b8d0 100755
--- a/django/forms/fields.py
+++ b/django/forms/fields.py
@@ -1078,6 +1078,9 @@ class MultiValueField(Field):
 class FilePathField(ChoiceField):
     def __init__(self, path, *, match=None, recursive=False, allow_files=True,
                  allow_folders=False, **kwargs):
+        # If path is a callable, call it to resolve the actual path string
+        if callable(path):
+            path = path()
         self.path, self.match, self.recursive = path, match, recursive
         self.allow_files, self.allow_folders = allow_files, allow_folders
         super().__init__(choices=(), **kwargs)
```

## Rules

### R1 — Must keep passing

All existing FilePathField tests must continue to pass unchanged

### R2 — Must not touch

Any test files - the fix must work with existing tests as-is

### R3 — Invariant

The `path` parameter must be a string when used in `os.walk()` and `os.scandir()` calls - if it's a callable, it must be resolved first
