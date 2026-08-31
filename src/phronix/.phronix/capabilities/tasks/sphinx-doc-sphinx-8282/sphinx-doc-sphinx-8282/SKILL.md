---
name: sphinx-doc-sphinx-8282
description: Fix Jinja2 import errors in Sphinx caused by missing pass_environment and related functions.
subject: sphinx-doc-sphinx-8282
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify import errors |
| `I2` | Instructions | Update jinja2glue imports |
| `I3` | Instructions | Update rst utility imports |
| `I4` | Instructions | Verify compatibility |
| `R1` | Rules | Do not alter other Jinja2 imports |
| `R2` | Rules | Maintain existing test behavior |

## Instructions

### I1 — Identify import errors

Run the test suite and note ImportError messages indicating missing `pass_environment` or `contextfunction` in Jinja2.

### I2 — Update jinja2glue imports

In `sphinx/jinja2glue.py`, replace the import of `contextfunction` with `pass_context`:
```diff
- from jinja2 import FileSystemLoader, BaseLoader, TemplateNotFound, contextfunction
+ from jinja2 import FileSystemLoader, BaseLoader, TemplateNotFound, pass_context as contextfunction
```

### I3 — Update rst utility imports

In `sphinx/util/rst.py`, replace the import of `environmentfilter` with `pass_environment`:
```diff
- from jinja2 import environmentfilter
+ from jinja2 import pass_environment as environmentfilter
```

### I4 — Verify compatibility

Run the Sphinx test suite again to ensure the ImportError is resolved and no new failures appear.

## Rules

### R1 — Do not alter other Jinja2 imports

Only change the specific imports mentioned; other Jinja2 functionality must remain unchanged to avoid breaking unrelated templates.

### R2 — Maintain existing test behavior

All existing regression tests must continue to pass after applying the changes.
