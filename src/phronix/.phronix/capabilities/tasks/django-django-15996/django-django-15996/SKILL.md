---
name: django-django-15996
description: The django-django-15996 subject.
subject: django-django-15996
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | serialize_combined_enum_flags |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — serialize_combined_enum_flags

Handle serialization of combined Enum flags (IntFlag/RegexFlag) in Django's EnumSerializer.

When serializing an enum value, check if it's a single member or a combined flag value.
For single members, use existing behavior: `module.EnumName['member_name']`.
For combined flags (where .name returns 'A|B' etc., not a valid member), decompose the value
by iterating through all enum members and finding those whose bits are set in the combined value.
If only one effective member, use single member syntax. If multiple members, generate OR expression
like `module.EnumName['A'] | module.EnumName['B']`.

The decomposition check: member.value & self.value.value == member.value identifies which
members' bits are subset of the combined value.

Steps:
1. Try to get self.value.name and verify enum_class[member_name].value == self.value.value
   - If valid, return single member serialization
2. If not valid (KeyError/AttributeError or value mismatch), decompose:
   - Iterate through enum_class members
   - Collect members where member.value & self.value.value == member.value
3. If exactly 1 matching member, use single member syntax
4. If multiple matching members, generate OR expression: " | ".join(
     [f"{module}.{enum_class.__qualname__}['{m.name}']" for m in matching_members]
   )

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/db/migrations/serializer.py b/django/db/migrations/serializer.py
index 38da1e6ecc..c41e851e30 100755
--- a/django/db/migrations/serializer.py
+++ b/django/db/migrations/serializer.py
@@ -125,10 +125,46 @@ class EnumSerializer(BaseSerializer):
     def serialize(self):
         enum_class = self.value.__class__
         module = enum_class.__module__
-        return (
-            "%s.%s[%r]" % (module, enum_class.__qualname__, self.value.name),
-            {"import %s" % module},
-        )
+
+        # Check if this is a single enum member or a combination (e.g., IntFlag with | operator)
+        # For combined flags, .name returns 'A|B' etc., which is not a valid member name
+        # We need to decompose the value into its constituent members
+
+        # Try to get the single member name first
+        try:
+            # If the value's name is a valid member, use the existing behavior
+            member_name = self.value.name
+            # Verify it's actually a valid member by checking if value matches
+            if enum_class[member_name].value == self.value.value:
+                return (
+                    "%s.%s[%r]" % (module, enum_class.__qualname__, member_name),
+                    {"import %s" % module},
+                )
+        except (KeyError, AttributeError):
+            pass
+
+        # For combined flags, decompose the value into individual members
+        # Iterate through all members and find those whose bits are set in the combined value
+        matching_members = []
+        for member in enum_class:
+            # Check if this member's value is a subset of the combined value
+            if member.value & self.value.value == member.value:
+                matching_members.append(member.name)
+
+        if len(matching_members) == 1:
+            # Single effective member (edge case)
+            return (
+                "%s.%s[%r]" % (module, enum_class.__qualname__, matching_members[0]),
+                {"import %s" % module},
+            )
+
+        # Multiple members - generate OR expression
+        code_parts = [
+            "%s.%s[%r]" % (module, enum_class.__qualname__, member_name)
+            for member_name in matching_members
+        ]
+        result = " | ".join(code_parts)
+        return result, {"import %s" % module}
 
 
 class FloatSerializer(BaseSimpleSerializer):
```

## Rules
