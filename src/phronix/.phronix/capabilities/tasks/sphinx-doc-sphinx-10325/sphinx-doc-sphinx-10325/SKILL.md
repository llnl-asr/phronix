---
name: sphinx-doc-sphinx-10325
description: Enables :inherited-members: option in sphinx automodule to accept comma-separated list of class names to ignore, rather than just a single class name. Parses input into a set for membership checking, following the same pattern as members_set_option and exclude_members_option.
subject: sphinx-doc-sphinx-10325
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |
| `I6` | Instructions | inherited_members_option function |
| `I7` | Instructions | is_filtered_inherited_member method |
| `R1` | Rules | Backward compatibility |

## Instructions

### I1 — Problem description

Sphinx autodoc fails for inherited members, causing test_automodule_inherited_members to fail due to mismatched method list.

### I2 — Key idea

The :inherited-members: option must support a list of classes to ignore when documenting inherited members.

### I3 — Instructions to solve

1. Open the Sphinx configuration where automodule is used.
2. Modify the :inherited-members: option to accept a list of class names.
3. Update the documentation source to pass the list of classes to ignore, e.g., ``:inherited-members: list``.
4. Ensure the list includes classes like ``list``, ``set``, ``tuple`` to be ignored.
5. Run the failing test ``test_automodule_inherited_members`` to verify the method list matches expected output.

### I4 — Constraints and rules

- Do not alter any existing tests.
- Keep all other Sphinx configuration unchanged.
- The change must not affect documentation of non‑inherited members.
- All existing passing tests (5) must continue to pass.
- The fix must be backward compatible with Sphinx versions that do not support the list syntax; fallback to original behavior when the option is a boolean.

### I5 — Pitfalls and lessons

- Attempting to change the automodule directive to a string list caused a syntax error in Sphinx older than 5.0.
- Adding the list without handling the boolean fallback broke other modules that relied on ``:inherited-members:`` being a simple flag.
- Ensure the implementation checks the type of the option before treating it as a list.
- Verify that the documentation builds without warnings about unknown options.

### I6 — inherited_members_option function

In sphinx/ext/autodoc/__init__.py, modify the inherited_members_option function (around line 112-116) to parse comma-separated values into a set:

# Before:
else:
    return arg

# After:
return {x.strip() for x in arg.split(',') if x.strip()}

### I7 — is_filtered_inherited_member method

In the Documenter class in sphinx/ext/autodoc/__init__.py, modify the is_filtered_inherited_member method (around line 685) to handle both string (single class) and set of class names:

# Added before the loop:
# Handle both string (single class) and set of class names
excluded_classes = self.options.inherited_members
if isinstance(excluded_classes, str):
    excluded_classes = {excluded_classes}

# Changed the check from:
if cls.__name__ == self.options.inherited_members and cls != self.object:

# To:
if cls.__name__ in excluded_classes and cls != self.object:

## Rules

### R1 — Backward compatibility

If inherited-members is a single class name (no commas), it should still work as before - the string wrapping handles this
