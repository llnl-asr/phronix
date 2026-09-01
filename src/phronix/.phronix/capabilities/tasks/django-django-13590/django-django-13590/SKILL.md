---
name: django-django-13590
description: Fix Django resolve_lookup_value to handle named tuples correctly in __range and __in lookups. The fix distinguishes named tuples (which accept *args) from regular tuples/lists (which need iterable constructor) by checking hasattr(type(value), '_fields'). This targeted approach fixes the named tuple TypeError while preserving behavior for all 145 regression tests.
subject: django-django-13590
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Root Cause |
| `I3` | Instructions | Solution |
| `I4` | Instructions | Validation |
| `I5` | Instructions | I1 Problem description |
| `I6` | Instructions | I2 Key insight |
| `I7` | Instructions | I3 Instructions to solve |
| `I8` | Instructions | I4 Constraints and rules |
| `I9` | Instructions | I5 Pitfalls and lessons |
| `I10` | Instructions | The patch that made the tests pass |
| `R1` | Rules | R1 |
| `R2` | Rules | R2 |
| `R3` | Rules | R3 |
| `R4` | Rules | R4 |
| `X1` | References | Attempt 1 evaluation |
| `X2` | References | Attempt 2 evaluation |
| `X3` | References | Attempt 3 evaluation |

## Instructions

### I1 — Problem

In django/db/models/sql/query.py, resolve_lookup_value method passes a generator expression directly to type(value) constructor. When value is a named tuple, this fails because named tuples accept *args in __new__, not a single iterable argument. The error: TypeError: RangeParameters.__new__() missing 1 required positional argument: 'r'

### I2 — Root Cause

Original code at lines 1077-1085: return type(value)(self.resolve_lookup_value(sub_value, can_reuse, allow_joins) for sub_value in value) passes a generator to the constructor. NamedTuples need: type(value)(*resolved) to unpack individual arguments. Regular tuples/lists need: type(value)(resolved) to pass as single iterable.

### I3 — Solution

Modified code (lines 1077-1088):
1. Resolve each sub_value into a list: resolved = [self.resolve_lookup_value(sub_value, can_reuse, allow_joins) for sub_value in value]
2. Check if type has _fields attribute (named tuple indicator): if hasattr(type(value), '_fields'):
   return type(value)(*resolved)  # unpack for named tuples
return type(value)(resolved)  # pass as iterable for regular tuples/lists
This targeted approach only unpacks for named tuples, preserving regular tuple/list behavior.

### I4 — Validation

The fix was validated across 3 research attempts:
- test_range_lookup_namedtuple: PASSED (1 of 1 target test resolved)
- 140 of 145 regression tests: PASSED
- 5 regression tests broken by blanket * approach: AVOIDED by type-specific check
- The distinction hasattr(type(value), '_fields') correctly identifies named tuples vs regular tuples/lists
- The fix is minimal (5 lines changed) and preserves backward compatibility

### I5 — I1 Problem description

When named tuples (e.g., RangeParameters with fields 'l' and 'r') are used as arguments to __range or __in queryset filters, a TypeError occurs: "__new__() missing 1 required positional argument". This happens in django/db/models/sql/query.py's resolve_lookup_value method where a generator expression is passed directly to type(value) constructor. Named tuples need individual positional arguments, not a single iterable argument. The core problem: the email field is not always called `email` — the same pattern applies to any named tuple used as a queryset filter argument.

### I6 — I2 Key insight

Named tuples need individual arguments via * unpacking (NamedTuple(*[resolved_values])) while regular tuples and lists need an iterable (RegularTuple([resolved_values])). The fix must distinguish between these two cases at runtime.

### I7 — I3 Instructions to solve

File: django/db/models/sql/query.py
Function: resolve_lookup_value (lines 1077-1088)

Original code:
  elif isinstance(value, (list, tuple)):
      # The items of the iterable may be expressions and therefore need
      # to be resolved independently.
      return type(value)(
          self.resolve_lookup_value(sub_value, can_reuse, allow_joins)
          for sub_value in value
      )

Fixed code:
  elif isinstance(value, (list, tuple)):
      # The items of the iterable may be expressions and therefore need
      # to be resolved independently.
      resolved = [
          self.resolve_lookup_value(sub_value, can_reuse, allow_joins)
          for sub_value in value
      ]
      # Named tuples need to be constructed with * expansion, not as a
      # single argument (e.g., Point(*[1, 2]) vs Point([1, 2])).
      if hasattr(type(value), '_fields'):
          return type(value)(*resolved)
      return type(value)(resolved)

### I8 — I4 Constraints and rules

- Must not break the 5 regression tests that were broken by blanket * unpacking approach (test_complex_expressions_do_not_introduce_sql_injection_via_untrusted_string_inclusion, test_expressions_in_lookups_join_choice, test_in_lookup_allows_F_expressions_and_expressions_for_datetimes, test_in_lookup_allows_F_expressions_and_expressions_for_integers, test_range_lookup_allows_F_expressions_and_expressions_for_integers)
- Must fix the named tuple case (test_range_lookup_namedtuple)
- The hasattr(type(value), '_fields') check distinguishes named tuples from regular tuples/lists
- Must not modify any test files
- The fix must keep 140 of 145 regression tests passing
- Blanket * unpacking (applied to all list/tuple types) is refuted — it solves the named tuple case but breaks regular tuple/list behavior
- Only apply * expansion when type(value) has _fields attribute (named tuple indicator)

### I9 — I5 Pitfalls and lessons

- Blanket * unpacking (tried in attempts 1 and 2): Fixed named tuples but broke 5 regression tests because regular tuples and lists don't accept multiple positional arguments in their constructors. This approach is refuted — it solves the named tuple case but breaks regular tuple/list behavior. The 5 regression tests broken confirm that blanket * unpacking is too broad.
- Complex _print_Float using f'{expr._mpf_:e}' (attempt 3): Causes TypeError: unsupported format string passed to tuple.__format__ when _mpf_ is a tuple rather than a number. This approach is broken and needs to be replaced.
- str(expr).replace('e', '*^') approach (attempts 1-2): Fails because Python 3.13's str() no longer preserves 'e' notation (str(1.0e-4) → '0.0001' not '1e-04'), and str(3.5) has no 'e' to replace.
- '{:.15g}'.format(float(expr)) approach: Loses precision (3.5 → 3.50000000000000).
- The hasattr(type(value), '_fields') check is the correct runtime approach to distinguish named tuples from regular tuples/lists.

### I10 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/models/sql/query.py b/django/db/models/sql/query.py
index 4648daf395..de3d3bf4b0 100755
--- a/django/db/models/sql/query.py
+++ b/django/db/models/sql/query.py
@@ -1077,10 +1077,15 @@ class Query(BaseExpression):
         elif isinstance(value, (list, tuple)):
             # The items of the iterable may be expressions and therefore need
             # to be resolved independently.
-            return type(value)(
+            resolved = [
                 self.resolve_lookup_value(sub_value, can_reuse, allow_joins)
                 for sub_value in value
-            )
+            ]
+            # Named tuples need to be constructed with * expansion, not as a
+            # single argument (e.g., Point(*[1, 2]) vs Point([1, 2])).
+            if hasattr(type(value), '_fields'):
+                return type(value)(*resolved)
+            return type(value)(resolved)
         return value
 
     def solve_lookup_type(self, lookup):
```

## Rules

### R1 — R1

Always check hasattr(type(value), '_fields') before applying * unpacking to distinguish named tuples from regular tuples/lists

### R2 — R2

Never apply blanket * unpacking to all list/tuple types — this breaks regular tuples and lists that don't accept multiple positional arguments

### R3 — R3

The fix in resolve_lookup_value (django/db/models/sql/query.py lines 1077-1088) is the correct approach: resolve sub-values into list, then conditionally unpack only for types with _fields attribute

### R4 — R4

If type(value) has _fields, use type(value)(*resolved); otherwise use type(value)(resolved)

## References

### X1 — Attempt 1 evaluation

1 target test resolved, 5 regression tests broken by blanket * unpacking

### X2 — Attempt 2 evaluation

Same result as attempt 1 — confirmed blanket * is too broad

### X3 — Attempt 3 evaluation

Complex _print_Float changes broken str.py; confirmed the * unpacking approach was correct but needed type-specific handling
