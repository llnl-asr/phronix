---
name: django-django-11583
description: The django-django-11583 subject.
subject: django-django-11583
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Handle embedded null byte paths in autoreload |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Do not alter other autoreload logic |

## Instructions

### I1 — Handle embedded null byte paths in autoreload

1. Open `django/utils/autoreload.py`.
2. In `iter_modules_and_files`, locate the line `resolved_path = path.resolve(strict=True).absolute()`.
3. Replace it with a try/except block:
   ```python
   try:
       resolved_path = path.resolve(strict=True).absolute()
   except ValueError:
       # Skip paths with embedded null bytes which cause ValueError
       continue
   ```
4. In `sys_path_directories`, similarly wrap the `resolved_path = path.resolve(strict=True).absolute()` line with the same try/except block and `continue` on `ValueError`.
5. Save the file and run the test suite to verify that all existing tests pass and the autoreload null‑byte error is resolved.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/utils/autoreload.py b/django/utils/autoreload.py
index 25c3b44250..0d0cc1dac7 100755
--- a/django/utils/autoreload.py
+++ b/django/utils/autoreload.py
@@ -139,9 +139,10 @@ def iter_modules_and_files(modules, extra_files):
         path = Path(filename)
         try:
             resolved_path = path.resolve(strict=True).absolute()
-        except FileNotFoundError:
+        except (FileNotFoundError, ValueError):
             # The module could have been removed, don't fail loudly if this
-            # is the case.
+            # is the case. ValueError is raised for paths with embedded null
+            # characters (e.g. certain Samba share configurations).
             continue
         results.add(resolved_path)
     return frozenset(results)
@@ -187,7 +188,7 @@ def sys_path_directories():
         path = Path(path)
         try:
             resolved_path = path.resolve(strict=True).absolute()
-        except FileNotFoundError:
+        except (FileNotFoundError, ValueError):
             continue
         # If the path is a file (like a zip file), watch the parent directory.
         if resolved_path.is_file():
```

## Rules

### R1 — Do not alter other autoreload logic

The added try/except blocks must only skip paths with embedded null bytes; all other path resolution behavior should remain unchanged to preserve existing functionality.
