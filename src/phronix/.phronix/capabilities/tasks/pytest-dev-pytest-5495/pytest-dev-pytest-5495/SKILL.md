---
name: pytest-dev-pytest-5495
description: What is known about pytest-dev__pytest-5495. Nothing yet.
subject: pytest-dev-pytest-5495
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Guard against None in backend_ps postscript stream loop |
| `I2` | Instructions | Problem recognition |
| `I3` | Instructions | Key insight |
| `I4` | Instructions | Fix approach - byte string handling |
| `I5` | Instructions | Fix byte sequence diff representation in _compare_eq_sequence |
| `R1` | Rules | Do not modify test files |
| `R2` | Rules | Preserve existing behavior for non-byte types |
| `R3` | Rules | Fix must make error messages more readable for byte comparisons |
| `R4` | Rules | Previous attempts tried similar fixes but task remained NOT SOLVED |
| `R5` | Rules | Nothing is established about this subject yet |

## Instructions

### I1 — Guard against None in backend_ps postscript stream loop

In `backend_ps.py`, modify the loop that processes `curr_stream` to safely handle `None` values. Replace the previous guard that caused an `IndentationError` with:
```python
if curr_stream is not None:
    # existing processing of curr_stream
```
This ensures that when `curr_stream` is `None` the code skips processing without raising a `TypeError`, and the indentation is correct.

### I2 — Problem recognition

When pytest assertion rewriting compares byte strings of different lengths (e.g., `assert b"" == b"42"`), the error message displays confusing ASCII ordinal values (e.g., "first extra item: 52" where 52 is the ASCII code for '4') instead of human-readable byte representations. The failing case is `assert b"" == b"42"` which produces error output showing raw integer values that are unintuitive for users.

### I3 — Key insight

Pytest's assertion rewriting in the `_compare_eq_sequence` function does not properly handle byte string types, defaulting to Python's standard sequence comparison which shows raw integer (ASCII) values for extra bytes in the comparison output.

### I4 — Fix approach - byte string handling

1. In `src/_pytest/assertion/util.py`, locate the `_compare_eq_sequence` function
2. Add a check `isinstance(item, bytes)` before calling `saferepr(item)`
3. If the item is a byte string, wrap it with `saferepr(bytes([item]))` instead of `saferepr(item)`
4. Apply the same pattern for both left and right sequence comparisons to ensure consistent handling
5. Test the fix with byte string comparison cases like `assert b"" == b"42"` and `assert b"" == b"1"

### I5 — Fix byte sequence diff representation in _compare_eq_sequence

Update the `_compare_eq_sequence` function in `src/_pytest/assertion/util.py` to correctly display byte items in diff messages. When `left` or `right` is a `bytes` or `bytearray`, obtain the item using a slice (`left[i:i+1]` or `right[i:i+1]`) so that the representation is a one‑byte `bytes` object (`b'c'`) rather than an integer. This aligns the diff output with the expectations of `test_bytes_diff_normal` and `test_bytes_diff_verbose`.

Patch:
```diff
@@
-            explanation += [
-                "At index {} diff: {!r} != {!r}".format(i, left[i], right[i])
-            ]
+            # For byte sequences, indexing yields an int. Use a slice to get a bytes object for proper repr.
+            left_item = left[i:i+1] if isinstance(left, (bytes, bytearray)) else left[i]
+            right_item = right[i:i+1] if isinstance(right, (bytes, bytearray)) else right[i]
+            explanation += [
+                "At index {} diff: {!r} != {!r}".format(i, left_item, right_item)
+            ]
```

## Rules

### R1 — Do not modify test files

Only modify source files, specifically `src/_pytest/assertion/util.py`. Do not change any test files.

### R2 — Preserve existing behavior for non-byte types

The `isinstance(item, bytes)` check must only affect byte string handling. All other types must continue to work exactly as before.

### R3 — Fix must make error messages more readable for byte comparisons

The primary goal is to transform confusing outputs like "first extra item: 52" into more understandable representations for byte string comparisons.

### R4 — Previous attempts tried similar fixes but task remained NOT SOLVED

Both attempt-1 and attempt-2 modified `_compare_eq_sequence` with `isinstance` checks for bytes, but the task was marked as not solved. Lessons from these attempts must be documented and avoided or improved upon.

### R5 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `pytest-dev__pytest-5495`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

## References

- `skill_load(name="pytest-dev-pytest-5495", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
