---
name: sphinx-doc-sphinx-10325
description: Enables :inherited-members: option in sphinx automodule to accept comma-separated list of class names to ignore, rather than just a single class name. Parses input into a set for membership checking, following the same pattern as members_set_option and exclude_members_option.
subject: sphinx-doc-sphinx-10325
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | inherited_members_option function |
| `I2` | Instructions | is_filtered_inherited_member method |
| `I3` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Backward compatibility |

## Instructions

### I1 — inherited_members_option function

In sphinx/ext/autodoc/__init__.py, modify the inherited_members_option function (around line 112-116) to parse comma-separated values into a set:

# Before:
else:
    return arg

# After:
return {x.strip() for x in arg.split(',') if x.strip()}

### I2 — is_filtered_inherited_member method

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

### I3 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sphinx/ext/autodoc/__init__.py b/sphinx/ext/autodoc/__init__.py
index 62631f7ff..0eb100c68 100755
--- a/sphinx/ext/autodoc/__init__.py
+++ b/sphinx/ext/autodoc/__init__.py
@@ -113,8 +113,7 @@ def inherited_members_option(arg: Any) -> Union[object, Set[str]]:
     """Used to convert the :members: option to auto directives."""
     if arg in (None, True):
         return 'object'
-    else:
-        return arg
+    return {x.strip() for x in arg.split(',') if x.strip()}
 
 
 def member_order_option(arg: Any) -> Optional[str]:
@@ -681,8 +680,13 @@ class Documenter:
         """
         def is_filtered_inherited_member(name: str, obj: Any) -> bool:
             if inspect.isclass(self.object):
+                # Handle both string (single class) and set of class names
+                excluded_classes = self.options.inherited_members
+                if isinstance(excluded_classes, str):
+                    excluded_classes = {excluded_classes}
+
                 for cls in self.object.__mro__:
-                    if cls.__name__ == self.options.inherited_members and cls != self.object:
+                    if cls.__name__ in excluded_classes and cls != self.object:
                         # given member is a member of specified *super class*
                         return True
                     elif name in cls.__dict__:
```

## Rules

### R1 — Backward compatibility

If inherited-members is a single class name (no commas), it should still work as before - the string wrapping handles this
