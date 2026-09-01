---
name: sphinx-doc-sphinx-8801
description: The sphinx-doc-sphinx-8801 subject.
subject: sphinx-doc-sphinx-8801
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | sphinx-doc-sphinx-8801 diagnosis |
| `I2` | Instructions | keyfunc2 and keyfunc3 interaction |
| `I3` | Instructions | importer.py inherited members fix |
| `I4` | Instructions | test impact and why it matters |
| `I5` | Instructions | attempt evolution observation |
| `I6` | Instructions | What problem it solves |
| `I7` | Instructions | The key idea |
| `I8` | Instructions | Instructions to solve it |
| `I9` | Instructions | Constraints and rules |
| `I10` | Instructions | Pitfalls and lessons |











## Instructions

### I1 — sphinx-doc-sphinx-8801 diagnosis

### I2 — keyfunc2 and keyfunc3 interaction

### I3 — importer.py inherited members fix

### I4 — test impact and why it matters

### I5 — attempt evolution observation

### I6 — What problem it solves

Sphinx autodoc with :inherited-members: directive does not properly document inherited class attributes that have PEP-526 type annotations (e.g., `x: int`) but no explicit doc comments. The target test `tests/test_ext_autodoc_autoclass.py::test_uninitialized_attributes` fails because these annotation-only members are filtered out by `filter_members` in `sphinx/ext/autodoc/__init__.py` at line 787 where `keep = has_doc or self.options.undoc_members` and `has_doc = bool(doc)` with `doc = getdoc(member, ...)` returns `None` for members that only have type annotations. The symptom a later run would recognise: when using `.. autoclass:: Example.Bar` with `:inherited-members:`, inherited members that have type annotations but no docstring do not appear in the output, even though they should be documented via their type annotations.

### I7 — The key idea

The `has_doc`/`getdoc()` determination does not properly handle annotation-only members (those marked with `INSTANCEATTR` sentinel from PEP-526 type annotations like `attr: int` without a doc comment), so when `:inherited-members:` triggers `want_all`, these members are incorrectly excluded from output despite having documentation value through their type annotations. The core bottleneck is at `sphinx/ext/autodoc/__init__.py:731` (`has_doc = bool(doc)`) and `:787` (`keep = has_doc or self.options.undoc_members`), not at the member collection or sorting stage.

### I8 — Instructions to solve it

Edit `sphinx/ext/autodoc/__init__.py` in the `filter_members` method. The attempt-1 broad fix that added `(want_all and member is INSTANCEATTR)` to the `keep` condition at line 787 must be refined — it caused 10 extra items to appear in test output, breaking ordering expectations (first extra: `:module: target.uninitialized_attributes`, ordering diff at index 12: `Derived.attr2` != `Derived.attr3`). A later run should implement a more targeted approach that selectively includes annotation-only members only in the inherited-members context without unconditionally adding all INSTANCEATTR members. The line change at 787 should replace the current `keep = has_doc or self.options.undoc_members` with a condition that checks whether the member is an INSTANCEATTR sentinel within the inherited-members path, using care to not include annotation-only members that have no documentation value whatsoever. Must maintain all 8 regression test passes.

### I9 — Constraints and rules

All 8 regression tests in `tests/test_ext_autodoc_autoclass.py` must continue to pass unchanged. The `undoc_members` option behavior must not be modified. The `want_all` flag (from `:inherited-members:`) should continue to work as before for non-annotation members. Only annotation-only members that have type annotations serving as documentation should be selectively included; members with no documentation value at all must remain filtered out. No changes to test files — only source code edits in `sphinx/ext/autodoc/__init__.py`. The fix must not introduce any new items beyond what the target test expects. The 8 already-passing regression tests must continue to pass as-is.

### I10 — Pitfalls and lessons

Attempt 1's broad INSTANCEATTR addition (`keep = has_doc or self.options.undoc_members or (want_all and member is INSTANCEATTR)`) caused 10 extra items to appear, first extra: `:module: target.uninitialized_attributes`, with ordering differences at index 12 (`Derived.attr2` != `Derived.attr3`). Lesson: adding INSTANCEATTR unconditionally when `want_all` is True is too broad and includes members that should not be documented. Attempt 2's sorting fix (keyfunc3 chr(127) handling) and inherited member collection enhancement (importer.py `get_class_members`) both failed to address the core filtering problem — they are partial fixes that don't reach the root cause in `filter_members`'s `has_doc` determination. Lesson: these approaches, while valuable for other reasons, do not solve the annotation-only member documentation problem. The `chr(127)` prepending issue in keyfunc2/keyfunc3 was a red herring for the core bug — it affected index entry grouping but not the `has_doc`/`getdoc()` determination. Regression tests (8/8) passed in both attempts, confirming no regressions were introduced — this is critical and must be maintained in any future fix. The `has_doc = bool(doc)` determination via `getdoc()` returning `None` for annotation-only members is the real bottleneck that any fix must address.

## Critical Observation: Diagnosis Not Evolved Between Attempts 2 and 3

Important: Diagnosis content was **identical** between attempts 2 and 3 of this task. This means:

1. Future attempts will read the same diagnosis and cannot build on prior work
2. The diagnosis was not evolved or refined between consecutive attempts
3. This is a lesson for future work: each attempt should update/refine the diagnosis to capture new findings

## How to Apply

When working on this task in future attempts:
- Always update the diagnosis with new findings, even if the core fix remains the same
- Note what was tried, what failed, and what was learned
- This ensures each attempt has unique, buildable context rather than identical starting points

## Test Impact

`tests/test_ext_autodoc_autoclass.py::test_uninitialized_attributes` fails:

- Expected: `Bar.attr1`, `Bar.attr2`, `Bar.attr3` all documented
- Actual: Only `Bar.attr2` and `Bar.attr3` documented; `Bar.attr1` (inherited from `Foo`) missing
- 8 regression tests pass, 1 target test fails
- Failure at index 5: `'.. py:attribute:: Derived.attr3' != '.. py:attribute:: Derived.attr1'`

## Why This Matters

Inherited attributes with `#: docstring` annotations are a common Python pattern. When Sphinx autodoc fails to document them, users lose visibility into the full API of a class hierarchy. This is especially critical for libraries and frameworks where understanding the complete inherited interface is essential for proper usage.

## Key Evidence

From `tests/roots/test-ext-autodoc/target/instance_variable.py`:
- `class Foo` with `attr1` (`#: docstring foo`) and `attr2` (`#: docstring foo`)
- `class Bar(Foo)` with `attr2` (`#: docstring bar`) and `attr3` (`#: docstring bar`)
- `Bar.attr1` (inherited) should be documented but currently is not

## Additional fix in sphinx/ext/autodoc/importer.py

The `get_class_members()` function needs to also match inherited members from parent classes in the same module. Current code only adds members not in superclass `__dict__`, but misses inherited members that have `#: docstring` annotations and should be documented.

The fix adds a check: if a member name exists in any parent class's `__dict__` (within the same module namespace), it should also be included as an ObjectMember for documentation purposes.

This ensures inherited attributes like `Bar.attr1` (from `class Bar(Foo)`) are properly collected and documented when they have `#: docstring` annotations in the parent class.

## Root Cause: keyfunc2 prepending chr(127)

In `sphinx/environment/adapters/indexentries.py`:

- **keyfunc2** (line ~553): Prepends `chr(127)` to any key starting with alpha or underscore
- **keyfunc3** (line ~536-541): Extracts first character to use as grouping letter; returns "Symbols" if not alpha/underscore

**Bug**: When keyfunc2 prepends chr(127) to an alpha key, keyfunc3 sees chr(127) as first character, which is neither alpha nor underscore, so routes entry to "Symbols" instead of proper group (e.g., "S" for "Foo").

This causes all alpha-prefixed members to be grouped under "Symbols" in index entries, making them invisible in expected documentation output.

## The Fix

In keyfunc3, strip chr(127) prefix before checking alpha status (after normalizing):

```python
k_normalized = unicodedata.normalize('NFD', k)
if k_normalized.startswith(chr(127)):
    k_normalized = k_normalized[1:]
letter = k_normalized[0].upper() if k_normalized else ''
```

This ensures entries artificially prefixed with chr(127) by keyfunc2 are grouped by their actual first character.

## Task Context

Issue #8801 in sphinx-doc project: Sphinx autodoc not documenting inherited class attributes with #: docstring annotations. Test `test_uninitialized_attributes` fails - expects `attr1` but gets `attr2` instead.

## Rules

## References
