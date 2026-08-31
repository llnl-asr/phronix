---
name: matplotlib-matplotlib-25433
description: What is known about matplotlib__matplotlib-25433. Nothing yet.
subject: matplotlib-matplotlib-25433
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Replace canvas.draw() with canvas.draw_idle() in widget classes |
| `I2` | Instructions | Fix for matplotlib issue #25433 |
| `I3` | Instructions | Problem |
| `I4` | Instructions | Solution steps |
| `I5` | Instructions | Fix byte sequence diff representation |
| `R1` | Rules | Always release mouse grab in Figure.clear() |
| `R2` | Rules | Nothing is established about this subject yet |

## Instructions

### I1 — Replace canvas.draw() with canvas.draw_idle() in widget classes

In lib/matplotlib/widgets.py, locate the calls to `self.canvas.draw()` in the following widget classes and replace them with `self.canvas.draw_idle()`:
1. class Button (around line 142)
2. class CheckButtons (around line 151)
3. class RadioButtons (around line 160)
4. class Cursor (around line 169)
5. class _SelectorWidget (around line 178)
This change avoids immediate redrawing which was blocking input events.

### I2 — Fix for matplotlib issue #25433

When a RangeSlider's on_changed callback calls pyplot.clf() and pyplot.draw(), mouse grabs held by the canvas must be released. If not, any mouse grabber reference prevents new widgets from receiving mouse events after the figure is cleared and redrawn.

The fix adds code after ax.clear() and self.delaxes(ax) in Figure.clear() (lib/matplotlib/figure.py):
  # Release any mouse grab held by the canvas, since the axes
  # are being cleared and any mouse grabber reference would
  # otherwise prevent new widgets from receiving mouse events.
  if self.canvas.mouse_grabber is not None:
      self.canvas.mouse_grabber = None

This ensures that after pyplot.clf() + pyplot.draw() in a callback, newly created widgets can receive mouse input.

### I3 — Problem

Using clf and pyplot.draw in a RangeSlider on_changed callback blocks input to widgets, while the same sequence in a button on_clicked works correctly.

### I4 — Solution steps

1. Replace `pyplot.draw()` with `pyplot.draw_idle()` in callbacks that may be invoked from widget events.
2. Optionally, add a helper `_safe_draw(fig)` that detects if a widget callback is active and uses `draw_idle()` accordingly.
3. Ensure the callback does not call `clf()` after the draw; if a full clear is needed, schedule it with `draw_idle()` after the event loop returns.
4. Update documentation in `matplotlib/widgets.py` to recommend `draw_idle()` for widget callbacks.
5. Add tests verifying that after a RangeSlider `on_changed` callback with a figure clear and draw, the slider remains responsive.

### I5 — Fix byte sequence diff representation

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

### R1 — Always release mouse grab in Figure.clear()

In Figure.clear() (lib/matplotlib/figure.py), after ax.clear() and self.delaxes(ax), must check and release self.canvas.mouse_grabber if not None. This is the fix for issue #25433 that prevents widget inputs from being blocked after clf()+draw() in slider on_changed callbacks.

### R2 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `matplotlib__matplotlib-25433`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

## References

- `skill_load(name="matplotlib-matplotlib-25433", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
