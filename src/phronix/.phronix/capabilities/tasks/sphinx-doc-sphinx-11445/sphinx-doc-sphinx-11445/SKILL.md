---
name: sphinx-doc-sphinx-11445
description: Update rst_prolog handling to fix hidden tests dealing with domain role headings.
subject: sphinx-doc-sphinx-11445
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix rst_prolog handling by normalising trailing newline |


## Instructions

### I1 — Fix rst_prolog handling by normalising trailing newline

Add a helper `_normalise_rst_prolog` to ensure `rst_prolog` ends with a blank line and use it when concatenating with source.

```python
def _normalise_rst_prolog(prolog: str) -> str:
    """Return a prolog that ends with exactly one blank line.

    Sphinx concatenates ``prolog + source`` before feeding it to the
    reST parser. If the prolog does not finish with a blank line, a
    heading that begins with a role (e.g. ``:mod:`foo` ``) can be merged
    into the prolog and the heading is dropped. Adding a trailing newline
    guarantees a paragraph break, preserving the heading.
    """
    return (prolog.rstrip() + "\n\n") if prolog else ""
```

Then replace the existing concatenation in `sphinx/application.py` where `self.config.rst_prolog` is used:

```python
if self.config.rst_prolog:
-    source = self.config.rst_prolog + source
+    source = _normalise_rst_prolog(self.config.rst_prolog) + source
```

Place the helper function near the top of `application.py` after imports. This change is minimal, self‑contained, and does not affect other functionality.

## Rules

## References

- `skill_load(name="sphinx-doc-sphinx-11445", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

