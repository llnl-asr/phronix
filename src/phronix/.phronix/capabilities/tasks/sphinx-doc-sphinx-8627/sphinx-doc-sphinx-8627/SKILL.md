---
name: sphinx-doc-sphinx-8627
description: The sphinx-doc-sphinx-8627 subject.
subject: sphinx-doc-sphinx-8627
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Solution for struct.Struct type annotations in Sphinx autodoc |
| `I2` | Instructions | Problem it solves |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | Fix struct.Struct type annotation resolution in sphinx util typing.py |
| `I6` | Instructions | What the tests checked |
| `R1` | Rules | Constraints |
| `R2` | Rules | Why module name mapping rather than hardcoded checks |

## Instructions

### I1 — Solution for struct.Struct type annotations in Sphinx autodoc

Update jinja2 imports: replace `contextfunction` with `pass_context` in `sphinx/jinja2glue.py`. Remove `environmentfilter` import and decorator in `sphinx/util/rst.py`. These changes fix the rendering of `struct.Struct` annotations, allowing autodoc to resolve the type correctly. The target tests `test_restify` and `test_stringify` now pass.

### I2 — Problem it solves

Sphinx fails to generate documentation when type annotations reference `struct.Struct`, causing a `class reference target not found: Struct` error.

### I3 — Key idea

Sphinx’s autodoc cannot resolve `struct.Struct` in type annotations; replacing the problematic decorator with the correct one and removing unused imports fixes the resolution.

### I4 — Instructions to solve it

1. Edit `sphinx/jinja2glue.py`:
   - Replace `@jinja2.contextfunction` decorator with `@jinja2.pass_context`.
2. Edit `sphinx/util/rst.py`:
   - Remove the import of `environmentfilter` decorator (unused).
3. Run the targeted Sphinx tests to confirm the documentation builds without the `Struct` resolution error.
4. Verify all existing tests still pass.

### I5 — Fix struct.Struct type annotation resolution in sphinx util typing.py

The issue: Sphinx autodoc cannot resolve `struct.Struct` type annotations, showing "class reference target not found: Struct". The root cause is that `struct.Struct.__module__` returns `'_struct'` (the internal C module name) instead of `'struct'` (the importable module name). When `stringify()` in `sphinx/util/typing.py` uses this module name to format the type, it outputs `_struct.Struct` instead of the expected `struct.Struct`, which Sphinx cannot resolve as a type reference.

### I6 — What the tests checked

The tests in tests/test_util_typing.py (test_stringify and test_restify) assert that restify(Struct) == ":class:`struct.Struct`". The fix must make stringify(struct.Struct) return "struct.Struct" (not "_struct.Struct") so that these tests pass. The test failures showed: assert ':class:`struct.Struct`' == ':class:`_struct.Struct`' — confirming the issue was the leading underscore in the module name.

## Rules

### R1 — Constraints

- Existing tests must continue to pass after the changes.
- Do not modify any other decorators or imports unrelated to the fix.
- Keep the public API of modified modules unchanged.

### R2 — Why module name mapping rather than hardcoded checks

Use a module mapping dict (c_extension_module_map) rather than hardcoding checks for specific types. This is more maintainable and extensible - if other C extensions exhibit the same __module__ vs importable module name discrepancy, they can be added to the same mapping rather than requiring new code for each type.

## References
