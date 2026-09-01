---
name: matplotlib-matplotlib-23913
description: Skill capturing the draggable parameter implementation for matplotlib Legend constructor. When a later run encounters a failing test about Legend not accepting draggable parameter, they can load this skill to understand the fix: add draggable=None keyword-only parameter after * in Legend.__init__(), when True automatically create DraggableLegend instance, when False/None set _draggable=None for backward compatibility. Five sections: problem, key idea, instructions, constraints, pitfalls.
subject: matplotlib-legend-draggable
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — What problem it solves

The Legend constructor does not accept a `draggable` keyword parameter despite having `set_draggable()` and `get_draggable()` methods and a `DraggableLegend` class already existing in the codebase. Users who want draggable legends must manually create `DraggableLegend` instances after calling `ax.legend()` or `plt.legend()`, which is inconsistent with the standard API pattern where the `loc` parameter and other legend properties are set at creation time. The symptom a later run would recognize: calling `ax.legend(draggable=True)` raises TypeError: __init__() got an unexpected keyword argument 'draggable', even though `l.set_draggable(True)` works afterward.

### I2 — The key idea

Add a `draggable=None` keyword-only parameter after `*` in `Legend.__init__()`; when `True`, automatically create a `DraggableLegend` instance using the legend's artist and connect the necessary event handlers, when `False` or `None`, set `_draggable=None` for backward compatibility so the existing `set_draggable()`/`get_draggable()` methods continue to work as the sole means of enabling dragging.

### I3 — Instructions to solve it

1. In `lib/matplotlib/legend.py`, locate the `Legend.__init__()` method signature and add `*, draggable=None` after the existing `*` separator (making it a keyword-only parameter that defaults to `None`).

2. After the existing `self._draggable = draggable` assignment (which sets `self._draggable = None` by default), add a conditional block:
   ```python
   if self._draggable is True:
       DraggableLegend(self.artist)
   ```

3. Ensure the existing `set_draggable(self, draggable)` and `get_draggable(self)` methods remain unchanged and continue to work — the new `__init__` parameter merely provides a convenient initialization shortcut. After the changes, `ax.legend(draggable=True)` should create a draggable legend without requiring a separate `l.set_draggable(True)` call, and `ax.legend()` or `ax.legend(draggable=False)` / `ax.legend(draggable=None)` should produce identical behavior to the pre-change `ax.legend()` call.

4. Verify that all 101 existing legend tests still pass with no regressions, particularly tests for `loc`, `bbox_to_anchor`, `fontsize`, and other existing `ax.legend()` parameters.

### I4 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/lib/matplotlib/legend.py b/lib/matplotlib/legend.py
index 9e5b903d59..b49aff7e48 100755
--- a/lib/matplotlib/legend.py
+++ b/lib/matplotlib/legend.py
@@ -342,7 +342,8 @@ class Legend(Artist):
         title_fontproperties=None,  # properties for the legend title
         alignment="center",       # control the alignment within the legend box
         *,
-        ncol=1  # synonym for ncols (backward compatibility)
+        ncol=1,  # synonym for ncols (backward compatibility)
+        draggable=None,  # bool, optional
     ):
         """
         Parameters
@@ -537,7 +538,11 @@ class Legend(Artist):
             title_prop_fp.set_size(title_fontsize)
 
         self.set_title(title, prop=title_prop_fp)
-        self._draggable = None
+
+        if draggable:
+            self._draggable = DraggableLegend(self)
+        else:
+            self._draggable = None
 
         # set the text color
```

## Rules
