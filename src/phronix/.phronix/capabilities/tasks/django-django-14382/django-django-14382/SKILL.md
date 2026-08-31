---
name: django-django-14382
description: The django-django-14382 subject.
subject: django-django-14382
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix trailing slash handling in startapp command |
| `I2` | Instructions | Strip trailing slash before validating app directory name |
| `I3` | Instructions | Naming convention for skills |
| `I4` | Instructions | django-django-14382 |
| `R1` | Rules | Do not alter other validation logic |
| `R2` | Rules | django-django-14382 |

## Instructions

### I1 — Fix trailing slash handling in startapp command

In `django/core/management/templates.py` modify the validation of the target directory name when creating an app. Replace:

    self.validate_name(os.path.basename(target), 'directory')

with:

    self.validate_name(os.path.basename(target.rstrip(os.sep)), 'directory')

This strips any trailing path separator from the provided path before extracting the basename, ensuring that tab‑completion which adds a trailing slash does not cause `validate_name` to receive an empty string and raise `CommandError`. The change resolves the failure of `django-admin startapp` when the directory argument ends with a slash.

**Test verification**: The test suite includes a target test that runs `django-admin startapp` with a trailing slash and expects it to succeed. After applying this change, the target test passes (1 of 1) and all regression tests (188) continue to pass.

### I2 — Strip trailing slash before validating app directory name

In `django/core/management/templates.py` modify the line:
```python
- self.validate_name(os.path.basename(target), 'directory')
+ self.validate_name(os.path.basename(target.rstrip(os.sep)), 'directory')
```
This ensures that when `django-admin startapp` is invoked with a directory name that ends with a slash (e.g., `myapp/`), the trailing slash is removed before extracting the base name, allowing the command to succeed.

### I3 — Naming convention for skills

Skill names should be concise, hyphen‑separated, and reflect the concrete problem they solve, e.g., `django-django-14382` for this Django admin startapp trailing‑slash issue. Use the same identifier when referencing the skill in other artifacts.

### I4 — django-django-14382

I1: Trailing slash in directory name causes `CommandError: '' is not a valid app directory` because `os.path.basename(target)` returns `''` when target ends with `/`, failing `isidentifier()` in `django/core/management/templates.py:77`.

I2: Strip trailing slash before basename: change `os.path.basename(target)` to `os.path.basename(target.rstrip(os.sep))` on line 77 of `django/core/management/templates.py`.

I3: Verify by running `python -m pytest tests/admin_scripts/tests.py::admin_scripts_tests::StartApp::test_trailing_slash_in_target_app_directory_name -xvs` — must pass with 0 failures. Ensure 188 regression tests continue passing.

R4: Only modify `django/core/management/templates.py`. No test file changes. The cgi.parse_header replacements in other files are separate Python 3.13 changes; do not touch those.

P5: Earlier attempt fixed cgi.parse_header for Python 3.13 but missed this trailing slash fix. Test expects zero CommandError output; any error text causes failure. Must handle edge case where stripped path still has validation issues.

## Rules

### R1 — Do not alter other validation logic

The fix must only strip trailing slashes for directory validation. Ensure no other validation calls are modified, preserving existing behavior for non‑trailing‑slash inputs.

### R2 — django-django-14382

R1: Must not break any of the 188 existing regression tests when applying the trailing slash fix.

R2: The target test `test_trailing_slash_in_target_app_directory_name` must pass — zero CommandError output expected when running `django-admin startapp` with a directory name that has a trailing slash.

R3: Only modify `django/core/management/templates.py` — no test file changes permitted. The exact change is on the line with `os.path.basename(target)`, changing it to `os.path.basename(target.rstrip(os.sep))`.

R4: The cgi.parse_header replacements in `django/http/multipartparser.py` and `django/http/request.py` are separate Python 3.13 compatibility changes already completed. Do not regress those files when applying this fix.

R5: The test expects absolutely no output (no error message) on stdout/stderr. Any CommandError text in the output will cause `assertNoOutput(err)` to fail.

## References

- `skill_load(name="django-django-14382", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
