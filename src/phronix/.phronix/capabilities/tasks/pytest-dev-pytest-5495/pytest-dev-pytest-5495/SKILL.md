---
name: pytest-dev-pytest-5495
description: What is known about pytest-dev__pytest-5495. Nothing yet.
subject: pytest-dev-pytest-5495
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix byte sequence diff representation in _compare_eq_sequence |
| `R1` | Rules | Nothing is established about this subject yet |



## Instructions

### I1 — Fix byte sequence diff representation in _compare_eq_sequence

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

### R1 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `pytest-dev__pytest-5495`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

## References

- `skill_load(name="pytest-dev-pytest-5495", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

