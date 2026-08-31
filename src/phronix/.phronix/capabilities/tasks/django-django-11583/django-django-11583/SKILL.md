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

## Rules

### R1 — Do not alter other autoreload logic

The added try/except blocks must only skip paths with embedded null bytes; all other path resolution behavior should remain unchanged to preserve existing functionality.

## References

- `skill_load(name="django-django-11583", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

