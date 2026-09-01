---
name: sphinx-doc-sphinx-8595
description: What is known about sphinx-doc-sphinx-8595: Handle empty __all__ in autodoc, Fix empty __all__ handling in autodoc
subject: sphinx-doc-sphinx-8595
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Handle empty __all__ in autodoc |
| `I2` | Instructions | Fix empty __all__ handling in autodoc |
| `I3` | Instructions | Problem it solves |
| `I4` | Instructions | Key idea |
| `I5` | Instructions | Instructions to solve it |
| `I6` | Instructions | Constraints and rules |
| `I7` | Instructions | The patch that made the tests pass |
| `R1` | Rules | What has been achieved so far, and what has not |

## Instructions

### I1 — Handle empty __all__ in autodoc

In `sphinx/ext/autodoc/__init__.py`, modify `ModuleDocumenter` to return `False, []` when `self.__all__` is empty, preventing any members from being documented. This fixes the `test_empty_all` case where an empty `__all__` should result in no members being shown.

```diff
@@ -1075,9 +1075,8 @@ class ModuleDocumenter(Documenter):
         members = self.get_module_members()
         if want_all:
             if not self.__all__:
-                # for implicit module members, check __module__ to avoid
-                # documenting imported objects
-                return True, list(members.values())
+                # Empty __all__ means no members should be documented
+                return False, []
             else:
                 for member in members.values():
                     if member.__name__ not in self.__all__:
```

### I2 — Fix empty __all__ handling in autodoc

Update `ModuleDocumenter.get_object_members` to correctly handle empty `__all__`. Replace the condition `if not self.__all__:` with `if self.__all__ is None:` to document all members when `__all__` is missing. When `__all__` is defined (even empty), only include members whose names are in `self.__all__`. The implementation filters members accordingly and returns the appropriate list.","description":"Fix empty __all__ handling in Sphinx autodoc"}

### I3 — Problem it solves

The task fails because Sphinx autodoc still lists module members even when the module defines an empty `__all__ = []`. Autodoc should suppress all members in this case, matching the expected behavior that an empty `__all__` results in no documented symbols.

### I4 — Key idea

Sphinx autodoc checks `self.__all__` with a truthy test; an empty list is falsy, so the existing condition `if not self.__all__:` incorrectly treats it as missing and falls back to documenting all members. The fix is to treat an explicitly empty list as a signal to suppress all members, i.e., change the condition to `if self.__all__ is not None:` and then handle the empty case by returning an empty member list.

### I5 — Instructions to solve it

Edit `src/flask/cli.py` (as shown in the diff) to compute a domain column only when needed and to set the header to "Host" or "Subdomain" accordingly. Specifically:
1. Determine sorting for rules and store in `sorted_rules`.
2. Compute `host_matching`, `server_name`, and for each rule compute `domain` per the logic in the diff.
3. Set `has_domain` flag.
4. Build `headers` as either `("Host", "Endpoint", "Methods", "Rule")` or `("Endpoint", "Methods", "Rule")` based on `has_domain`.
5. Adjust width calculations and row formatting to include the optional domain column.
6. Ensure the table output respects the new column ordering.
The change must be correctly indented to match surrounding code.

### I6 — Constraints and rules

* Do not modify any other part of `src/flask/cli.py` beyond the `routes_command` implementation.
* All existing tests unrelated to the routes command must continue to pass (75 existing passing tests). 
* The new column header must be exactly "Host" when `url_map.host_matching` is true, otherwise "Subdomain". No generic "Domain" header is allowed.
* The column should only appear when at least one rule has a non‑empty domain value; otherwise the table layout must remain unchanged (Endpoint stays in column 0).
* Preserve the original column order for the other fields (Endpoint, Methods, Rule) and keep the existing width calculations logic.
* The implementation must be syntactically correct and respect the project's code style (PEP 8).

### I7 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sphinx/ext/autodoc/__init__.py b/sphinx/ext/autodoc/__init__.py
index d85d79617..619ecef12 100755
--- a/sphinx/ext/autodoc/__init__.py
+++ b/sphinx/ext/autodoc/__init__.py
@@ -1074,7 +1074,12 @@ class ModuleDocumenter(Documenter):
     def get_object_members(self, want_all: bool) -> Tuple[bool, ObjectMembers]:
         members = self.get_module_members()
         if want_all:
-            if not self.__all__:
+            if self.__all__ is None:
+                # No __all__ defined: document all members
+                return True, list(members.values())
+            elif self.__all__ == []:
+                # Empty __all__: document no members
+                return False, []
                 # for implicit module members, check __module__ to avoid
                 # documenting imported objects
                 return True, list(members.values())
```

## Rules

### R1 — What has been achieved so far, and what has not

**Already passing (1 of 1).** Do not rewrite the code that makes these pass — they are the part that works:
- `tests/test_ext_autodoc_automodule.py::test_empty_all`

Measured after try 1.
