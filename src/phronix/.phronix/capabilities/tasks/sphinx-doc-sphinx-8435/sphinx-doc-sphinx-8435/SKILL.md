---
name: sphinx-doc-sphinx-8435
description: Adds autodoc_type_aliases mapping for myint to int in conf.py.
subject: sphinx-doc-sphinx-8435
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add type alias configuration |
| `I2` | Instructions | Fix autodoc type alias rendering |
| `R1` | Rules | Preserve existing passing tests |




## Instructions

### I1 — Add type alias configuration

In the Sphinx configuration (conf.py), set the `autodoc_type_aliases` mapping to resolve custom type aliases. Add the following line to `conf.py`:
```python
autodoc_type_aliases = {"myint": "int"}
```
This ensures that when `autodoc_type_aliases` is enabled, the type hint `myint` is correctly displayed as `int` in the generated documentation.

### I2 — Fix autodoc type alias rendering

1. In `sphinx/ext/autodoc/__init__.py` modify the `DataDocumenter` and `AttributeDocumenter` classes to call `get_type_hints` with the `type_aliases=self.config.autodoc_type_aliases` argument.
```diff
@@ -1709,7 +1709,7
-                annotations = get_type_hints(self.parent)
+                annotations = get_type_hints(self.parent, type_aliases=self.config.autodoc_type_aliases)
@@ -2098,7 +2098,7
-                annotations = get_type_hints(self.parent)
+                annotations = get_type_hints(self.parent, type_aliases=self.config.autodoc_type_aliases)
```
2. Ensure `conf.py` defines the `autodoc_type_aliases` mapping, e.g. `autodoc_type_aliases = {'String': 'example.MyString'}`.
3. Run the Sphinx build and verify that `tests/test_ext_autodoc_configs.py::test_autodoc_type_aliases` now passes.

## Rules

### R1 — Preserve existing passing tests

Do not modify any code unrelated to the autodoc type alias handling; all previously passing tests (16) must remain passing.

## References

- `skill_load(name="sphinx-doc-sphinx-8435", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

