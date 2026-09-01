---
name: matplotlib-matplotlib-25433
description: What is known about matplotlib__matplotlib-25433. Nothing yet.
subject: matplotlib-matplotlib-25433
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Solution steps |
| `I3` | Instructions | Fix byte sequence diff representation |
| `R1` | Rules | Nothing is established about this subject yet |





## Instructions

### I1 — Problem

Using clf and pyplot.draw in a RangeSlider on_changed callback blocks input to widgets, while the same sequence in a button on_clicked works correctly.

### I2 — Solution steps

1. Replace `pyplot.draw()` with `pyplot.draw_idle()` in callbacks that may be invoked from widget events.
2. Optionally, add a helper `_safe_draw(fig)` that detects if a widget callback is active and uses `draw_idle()` accordingly.
3. Ensure the callback does not call `clf()` after the draw; if a full clear is needed, schedule it with `draw_idle()` after the event loop returns.
4. Update documentation in `matplotlib/widgets.py` to recommend `draw_idle()` for widget callbacks.
5. Add tests verifying that after a RangeSlider `on_changed` callback with a figure clear and draw, the slider remains responsive.

### I3 — Fix byte sequence diff representation

Update `_compare_eq_sequence` in `src/_pytest/assertion/util.py` to correctly display byte items in diff messages. When `left` or `right` is a `bytes` or `bytearray`, compare using `repr(left[i:i+1])` and `repr(right[i:i+1])` instead of the raw integer values. This restores the expected `b'c'` format for byte‑string diffs, making the two target tests pass.

Patch:
```diff
@@
-            explanation += [
-                "At index {} diff: {!r} != {!r}".format(i, left[i], right[i])
-            ]
+            # When comparing byte sequences, `left[i]` yields an int. Use a slice to get a one‑byte bytes object for proper representation.
+            left_item = left[i:i+1] if isinstance(left, (bytes, bytearray)) else left[i]
+            right_item = right[i:i+1] if isinstance(right, (bytes, bytearray)) else right[i]
+            explanation += [
+                "At index {} diff: {!r} != {!r}".format(i, left_item, right_item)
+            ]
```

## Rules

### R1 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `matplotlib__matplotlib-25433`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

## References

- `skill_load(name="matplotlib-matplotlib-25433", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

