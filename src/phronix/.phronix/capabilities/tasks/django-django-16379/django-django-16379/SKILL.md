---
name: django-django-16379
description: The problem: TOCTOU race condition in has_key where the file could disappear between the exists check and the open call
subject: django-django-16379
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add try/except around file opening in has_key |
| `I2` | Instructions | What problem it solves |
| `I3` | Instructions | The key idea |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | Pitfalls and lessons |
| `I6` | Instructions | L1: Check-then-use anti-pattern |
| `I7` | Instructions | L2: Concurrent vs single-threaded |
| `I8` | Instructions | L3: Mirror established pattern |
| `R1` | Rules | Do not change cache expiry logic |
| `R2` | Rules | What must keep passing |
| `R3` | Rules | What must not be touched |

## Instructions

### I1 — Add try/except around file opening in has_key

In `django/core/cache/backends/filebased.py`, modify the `has_key` method:
```python
def has_key(self, key, version=None):
    fname = self._key_to_file(key, version)
    if os.path.exists(fname):
        try:
            with open(fname, "rb") as f:
                return not self._is_expired(f)
        except FileNotFoundError:
            # File was removed after the exists check; treat as missing
            return False
    return False
```

### I2 — What problem it solves

Race condition in Django's FileBasedCache.has_key method: between os.path.exists(fname) and open(fname, "rb"), the file can be deleted (by _is_expired() itself or by concurrent processes), causing FileNotFoundError.

### I3 — The key idea

Replace the two-step `os.path.exists(fname)` + `open(fname, "rb")` pattern with a single `try/except FileNotFoundError` around `open()`, matching the pattern already used by `get()` in the same file. This eliminates the TOCTOU window entirely.

### I4 — Instructions to solve it

1. In `django/core/cache/backends/filebased.py`, replace the `has_key` method (lines 69-75):
   - Remove the `if os.path.exists(fname):` check
   - Wrap `with open(fname, "rb") as f:` in a `try` block
   - Add `except FileNotFoundError: return False` after the `with` block
   - The `return False` that was after the exists check now goes in the except clause

2. The method signature and all other code stay exactly the same. No imports needed since `FileNotFoundError` is a built-in Python exception.

3. Run the 2 target tests and 362 regression tests to verify the fix does not break anything.

### I5 — Pitfalls and lessons

P1: The old `os.path.exists(fname)` + `open(fname, "rb")` pattern creates a TOCTOU window.

P2: `_is_expired()` itself deletes the file when expired (line 157). A single-threaded run can trigger FileNotFoundError if the key is expired — not just concurrent access.

P3: The existing `get()` method in the same file already uses try/except FileNotFoundError. The fix mirrors this established pattern — no new solution needed.

### I6 — L1: Check-then-use anti-pattern

When a subsequent operation has destructive side effects (like _is_expired() deleting the file), the check-then-use pattern widens the TOCTOU window. Always use try/except when the open() can fail for reasons the exists() check doesn't cover.

### I7 — L2: Concurrent vs single-threaded

Race conditions that seem unlikely in single-threaded testing can surface in production with concurrent access. The fix must handle both: concurrent file deletion AND _is_expired()'s own deletion in single-threaded execution.

### I8 — L3: Mirror established pattern

Don't re-invent a different solution — the existing `get()` method in filebased.py already uses try/except FileNotFoundError around open(). Matching this pattern was the right call; it avoids introducing subtle behavior differences and leverages work already verified by the project's tests.

## Rules

### R1 — Do not change cache expiry logic

The fix must only handle missing files; do not alter how expiration is determined.

### R2 — What must keep passing

All 362 regression tests in cache.tests.DBCacheWithTimeZoneTests must continue to pass. The fix must not change the public behavior: keys that exist and are not expired still return True, keys that don't exist or are expired still return False. No test files may be modified.

### R3 — What must not be touched

- Do NOT modify any test files (as instructed)
- Do NOT add new imports
- Do NOT change the method signature
- The `_is_expired` method's behavior and its side effect of deleting expired files must remain unchanged
- Only the `has_key` method body is modified

## References
