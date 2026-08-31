---
name: django-django-11564
description: Support for SCRIPT_NAME in STATIC_URL and MEDIA_URL
subject: django-django-11564
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem solved |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions |
| `R1` | Rules | Do not modify test files |





## Instructions

### I1 — Problem solved

Static files (STATIC_URL) and media files (MEDIA_URL) are built without the SCRIPT_NAME prefix when the application is served under a sub‑path, causing URLs like `/static/...` instead of `<SCRIPT_NAME>/static/...`.

### I2 — Key idea

Prepend the WSGI SCRIPT_NAME value to STATIC_URL and MEDIA_URL at runtime, ensuring static and media URLs respect the application’s sub‑path deployment.

### I3 — Instructions

1. Open the project's ``settings.py``.
2. Import ``os`` if not already imported.
3. Add a helper to prepend ``SCRIPT_NAME`` at runtime:
   ```python
   def script_name_prefix(path):
       script = os.getenv('SCRIPT_NAME', '')
       return f"{script}{path}" if script else path
   ```
4. Replace the static definitions of ``STATIC_URL`` and ``MEDIA_URL`` with:
   ```python
   STATIC_URL = script_name_prefix('/static/')
   MEDIA_URL = script_name_prefix('/media/')
   ```
5. Save the file.
6. Open ``django/template/defaulttags.py`` and locate the ``StaticNode`` ``render`` method (around line 200).
7. Modify the URL construction to use the request's ``SCRIPT_NAME`` when available:
   ```python
   def render(self, context):
       url = self.url(context)
       request = context.get('request')
       script_name = getattr(request, 'META', {}).get('SCRIPT_NAME', '') if request else ''
       if script_name:
           url = f"{script_name}{url}"
       if self.varname is None:
           return url
       context[self.varname] = url
       return ''
   ```
8. Run the project's test suite covering static files to verify URLs include ``SCRIPT_NAME``.
9. Ensure no existing tests are modified; only the code changes above are applied.

## Rules

### R1 — Do not modify test files

All changes must be limited to source code; test files must remain unchanged to satisfy the task's judgment criteria.

## References
