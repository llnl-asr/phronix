---
name: sympy-sympy-13471
description: The sympy-sympy-13471 subject.
subject: sympy-sympy-13471
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix Python 2->3 pickle float compatibility |
| `I2` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Fix Python 2->3 pickle float compatibility

Issue: When a sympy expression containing a float is pickled in Python 2 and unpickled in Python 3, it fails with ValueError: invalid literal for int() with base 16: '1L'.

Root cause: In Python 2, hex strings from pickled objects may have a trailing 'L' suffix (Python 2's long integer representation). The code at sympy/core/numbers.py line 1045 used `long(num[1], 16)` which in Python 3's `long = int` alias would try to parse '1L' as hex, failing because 'L' is not valid hex.

Fix applied to sympy/core/numbers.py line 1045:
- Changed: num[1] = long(num[1], 16)
- To: num[1] = int(num[1].rstrip('L'), 16)
- Added comment: "# Python 2 pickled hex strings may have a trailing 'L' suffix"

Why this form: Using `int()` with `.rstrip('L')` handles both cases - hex strings with or without the Python 2 'L' suffix. The `long` name is already a compatibility alias in sympy.core.compatibility (aliased to `int` in Python 3), so the fix leverages that while stripping the trailing suffix.

Tests verified:
- int('1L'.rstrip('L'), 16) = 1  ✅
- int('1'.rstrip('L'), 16) = 1    ✅ (no regression)
- The one target test passes
- 82 regression tests continue to pass

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/core/numbers.py b/sympy/core/numbers.py
index 7bc96e68e..ad6d58088 100755
--- a/sympy/core/numbers.py
+++ b/sympy/core/numbers.py
@@ -1042,7 +1042,8 @@ def __new__(cls, num, dps=None, prec=None, precision=None):
                 # it's a hexadecimal (coming from a pickled object)
                 # assume that it is in standard form
                 num = list(num)
-                num[1] = long(num[1], 16)
+                # Python 2 pickled hex strings may have a trailing 'L' suffix
+                num[1] = int(num[1].rstrip('L'), 16)
                 _mpf_ = tuple(num)
             else:
                 if len(num) == 4:
```

## Rules
