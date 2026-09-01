---
name: django-django-10914
description: Fix default file upload permissions and compatibility import for Python 3.13 in Django.
subject: django-django-10914
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Set default FILE_UPLOAD_PERMISSIONS to 0o644 |
| `I2` | Instructions | Add compatibility import for cgi module |
| `R1` | Rules | Do not alter unrelated settings |
| `R2` | Rules | Maintain test suite passing |

## Instructions

### I1 — Set default FILE_UPLOAD_PERMISSIONS to 0o644

In django/conf/global_settings.py change the line `FILE_UPLOAD_PERMISSIONS = None` to `FILE_UPLOAD_PERMISSIONS = 0o644`.

### I2 — Add compatibility import for cgi module

In django/http/multipartparser.py replace the import of cgi with a try/except block:
```python
try:
    import cgi  # Compatibility import for Python 3.13 where cgi is removed
except ImportError:
    import urllib.parse as cgi
```

## Rules

### R1 — Do not alter unrelated settings

Only modify FILE_UPLOAD_PERMISSIONS and the cgi import. All other settings and code must remain unchanged.

### R2 — Maintain test suite passing

Changes must not break existing Django tests; the patch must apply cleanly.
