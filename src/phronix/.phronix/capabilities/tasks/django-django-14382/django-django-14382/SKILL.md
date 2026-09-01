---
name: django-django-14382
description: The django-django-14382 subject.
subject: django-django-14382
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | django-django-14382 |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | django-django-14382 |

## Instructions

### I1 — django-django-14382

I1: Trailing slash in directory name causes `CommandError: '' is not a valid app directory` because `os.path.basename(target)` returns `''` when target ends with `/`, failing `isidentifier()` in `django/core/management/templates.py:77`.

I2: Strip trailing slash before basename: change `os.path.basename(target)` to `os.path.basename(target.rstrip(os.sep))` on line 77 of `django/core/management/templates.py`.

I3: Verify by running `python -m pytest tests/admin_scripts/tests.py::admin_scripts_tests::StartApp::test_trailing_slash_in_target_app_directory_name -xvs` — must pass with 0 failures. Ensure 188 regression tests continue passing.

R4: Only modify `django/core/management/templates.py`. No test file changes. The cgi.parse_header replacements in other files are separate Python 3.13 changes; do not touch those.

P5: Earlier attempt fixed cgi.parse_header for Python 3.13 but missed this trailing slash fix. Test expects zero CommandError output; any error text causes failure. Must handle edge case where stripped path still has validation issues.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/core/management/templates.py b/django/core/management/templates.py
index 8dc6068286..f248ab1b71 100755
--- a/django/core/management/templates.py
+++ b/django/core/management/templates.py
@@ -74,7 +74,7 @@ class TemplateCommand(BaseCommand):
                 raise CommandError(e)
         else:
             if app_or_project == 'app':
-                self.validate_name(os.path.basename(target), 'directory')
+                self.validate_name(os.path.basename(target.rstrip(os.sep)), 'directory')
             top_dir = os.path.abspath(os.path.expanduser(target))
             if not os.path.exists(top_dir):
                 raise CommandError("Destination directory '%s' does not "
```

## Rules

### R1 — django-django-14382

R1: Must not break any of the 188 existing regression tests when applying the trailing slash fix.

R2: The target test `test_trailing_slash_in_target_app_directory_name` must pass — zero CommandError output expected when running `django-admin startapp` with a directory name that has a trailing slash.

R3: Only modify `django/core/management/templates.py` — no test file changes permitted. The exact change is on the line with `os.path.basename(target)`, changing it to `os.path.basename(target.rstrip(os.sep))`.

R4: The cgi.parse_header replacements in `django/http/multipartparser.py` and `django/http/request.py` are separate Python 3.13 compatibility changes already completed. Do not regress those files when applying this fix.

R5: The test expects absolutely no output (no error message) on stdout/stderr. Any CommandError text in the output will cause `assertNoOutput(err)` to fail.
