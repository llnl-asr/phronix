---
name: django-django-16379
description: The problem: TOCTOU race condition in has_key where the file could disappear between the exists check and the open call
subject: django-django-16379
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Pitfalls and lessons |
| `I5` | Instructions | L1: Check-then-use anti-pattern |
| `I6` | Instructions | L2: Concurrent vs single-threaded |
| `I7` | Instructions | L3: Mirror established pattern |
| `I8` | Instructions | The patch that made the tests pass |
| `R1` | Rules | What must keep passing |
| `R2` | Rules | What must not be touched |

## Instructions

### I1 — What problem it solves

Race condition in Django's FileBasedCache.has_key method: between os.path.exists(fname) and open(fname, "rb"), the file can be deleted (by _is_expired() itself or by concurrent processes), causing FileNotFoundError.

### I2 — The key idea

Replace the two-step `os.path.exists(fname)` + `open(fname, "rb")` pattern with a single `try/except FileNotFoundError` around `open()`, matching the pattern already used by `get()` in the same file. This eliminates the TOCTOU window entirely.

### I3 — Instructions to solve it

1. In `django/core/cache/backends/filebased.py`, replace the `has_key` method (lines 69-75):
   - Remove the `if os.path.exists(fname):` check
   - Wrap `with open(fname, "rb") as f:` in a `try` block
   - Add `except FileNotFoundError: return False` after the `with` block
   - The `return False` that was after the exists check now goes in the except clause

2. The method signature and all other code stay exactly the same. No imports needed since `FileNotFoundError` is a built-in Python exception.

3. Run the 2 target tests and 362 regression tests to verify the fix does not break anything.

### I4 — Pitfalls and lessons

P1: The old `os.path.exists(fname)` + `open(fname, "rb")` pattern creates a TOCTOU window.

P2: `_is_expired()` itself deletes the file when expired (line 157). A single-threaded run can trigger FileNotFoundError if the key is expired — not just concurrent access.

P3: The existing `get()` method in the same file already uses try/except FileNotFoundError. The fix mirrors this established pattern — no new solution needed.

### I5 — L1: Check-then-use anti-pattern

When a subsequent operation has destructive side effects (like _is_expired() deleting the file), the check-then-use pattern widens the TOCTOU window. Always use try/except when the open() can fail for reasons the exists() check doesn't cover.

### I6 — L2: Concurrent vs single-threaded

Race conditions that seem unlikely in single-threaded testing can surface in production with concurrent access. The fix must handle both: concurrent file deletion AND _is_expired()'s own deletion in single-threaded execution.

### I7 — L3: Mirror established pattern

Don't re-invent a different solution — the existing `get()` method in filebased.py already uses try/except FileNotFoundError around open(). Matching this pattern was the right call; it avoids introducing subtle behavior differences and leverages work already verified by the project's tests.

### I8 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/django/core/cache/backends/filebased.py b/django/core/cache/backends/filebased.py
index 631da49444..215fefbcc0 100755
--- a/django/core/cache/backends/filebased.py
+++ b/django/core/cache/backends/filebased.py
@@ -90,10 +90,11 @@ class FileBasedCache(BaseCache):
 
     def has_key(self, key, version=None):
         fname = self._key_to_file(key, version)
-        if os.path.exists(fname):
+        try:
             with open(fname, "rb") as f:
                 return not self._is_expired(f)
-        return False
+        except FileNotFoundError:
+            return False
 
     def _cull(self):
         """
```

## Rules

### R1 — What must keep passing

All 362 regression tests in cache.tests.DBCacheWithTimeZoneTests must continue to pass. The fix must not change the public behavior: keys that exist and are not expired still return True, keys that don't exist or are expired still return False. No test files may be modified.

### R2 — What must not be touched

- Do NOT modify any test files (as instructed)
- Do NOT add new imports
- Do NOT change the method signature
- The `_is_expired` method's behavior and its side effect of deleting expired files must remain unchanged
- Only the `has_key` method body is modified
