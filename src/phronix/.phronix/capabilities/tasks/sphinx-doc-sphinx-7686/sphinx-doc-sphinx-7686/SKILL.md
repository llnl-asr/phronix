---
name: sphinx-doc-sphinx-7686
description: The sphinx-doc-sphinx-7686 subject.
subject: sphinx-doc-sphinx-7686
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I2 — Correct Jinja2 import in rst.py |
| `I2` | Instructions | Identify import error in sphinx/util/rst.py |
| `I3` | Instructions | Apply fix in sphinx/util/rst.py |
| `R1` | Rules | Maintain existing import behavior for other Jinja2 filters |

## Instructions

### I1 — I2 — Correct Jinja2 import in rst.py

Update `sphinx/util/rst.py` to import the correct function from Jinja2.
```diff
@@
-    from jinja2 import pass_environment as environmentfilter
+    from jinja2 import environmentfilter
```

### I2 — Identify import error in sphinx/util/rst.py

When tests fail due to `ImportError: cannot import name 'pass_environment' from 'jinja2'`, recognize that the problematic line is `from jinja2 import environmentfilter`.

### I3 — Apply fix in sphinx/util/rst.py

In `sphinx/util/rst.py` replace the line:
```python
from jinja2 import environmentfilter
```
with:
```python
from jinja2 import pass_environment as environmentfilter
```
This resolves the ImportError for `environmentfilter`.

## Rules

### R1 — Maintain existing import behavior for other Jinja2 filters

Do not modify other Jinja2 imports; only replace `environmentfilter` with `pass_environment as environmentfilter` to preserve functionality elsewhere.

## References

- `skill_load(name="sphinx-doc-sphinx-7686", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
