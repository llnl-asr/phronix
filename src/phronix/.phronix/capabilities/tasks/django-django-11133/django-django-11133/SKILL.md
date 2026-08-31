---
name: django-django-11133
description: The django-django-11133 subject.
subject: django-django-11133
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add memoryview support to HttpResponse |
| `I2` | Instructions | HttpResponse memoryview content handling |
| `R1` | Rules | Naming convention for this fix |

## Instructions

### I1 — Add memoryview support to HttpResponse

In `django/http/response.py` modify `_convert_to_bytes`:
```python
@@
-        if isinstance(value, str):
-            return bytes(value.encode(self.charset))
+        if isinstance(value, str):
+            return bytes(value.encode(self.charset))
+        if isinstance(value, memoryview):
+            # Convert memoryview to bytes directly
+            return bytes(value)
```

### I2 — HttpResponse memoryview content handling

1. What problem it solves: HttpResponse(memoryview(b"content")) returns b'<memory at 0x...>' for .content instead of actual bytes. The make_bytes method in HttpResponseBase didn't handle memoryview objects.

2. The key idea: Added explicit memoryview check in make_bytes() using bytes(value) - Python's standard conversion that extracts underlying bytes from a memoryview.

3. Instructions to solve it: In django/http/response.py, HttpResponseBase.make_bytes() method, insert after the str isinstance check and before the final return:
   # Handle memoryview objects.
   if isinstance(value, memoryview):
       return bytes(value)
   This must be 2-3 lines placed before the generic fallback.

4. Constraints and rules: Keep all 64 regression tests passing. Only affect memoryview objects - other types (bytes, str, int, float) must behave exactly as before. The fix uses bytes(value) which is the standard Python way to convert memoryview, consistent with existing bytes(value) pattern in same method. Do not modify any test files.

5. Pitfalls and lessons: Memoryview objects from PostgreSQL database fields need this handling - without it, content shows <memory at 0x...>. The memoryview check must come before the generic str(value) fallback, otherwise it will still convert to string representation.

## Rules

### R1 — Naming convention for this fix

The skill is named after the failing test identifier (django-11133) and the project component (django). This ensures later runs can locate the fix via `skill_load("django-django-11133")`.

## References
