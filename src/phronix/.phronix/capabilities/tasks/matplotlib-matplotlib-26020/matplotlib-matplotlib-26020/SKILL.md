---
name: matplotlib-matplotlib-26020
description: Captures the _tick_only fix for matplotlib AxesGrid with non-default axis classes (GeoAxes, default matplotlib Axes). The skill documents: (1) the symptom (TypeError when using non-default axis_class), (2) the key insight (duck-typing check on ax.axis), (3) numbered instructions to apply the fix, (4) constraints and rules for backward compatibility, and (5) pitfalls and lessons from the original failure.
subject: matplotlib-matplotlib-26020
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/lib/mpl_toolkits/axes_grid1/axes_grid.py b/lib/mpl_toolkits/axes_grid1/axes_grid.py
index 2b1b1d3200..eb3dafd3e3 100755
--- a/lib/mpl_toolkits/axes_grid1/axes_grid.py
+++ b/lib/mpl_toolkits/axes_grid1/axes_grid.py
@@ -13,8 +13,19 @@ from .mpl_axes import Axes
 def _tick_only(ax, bottom_on, left_on):
     bottom_off = not bottom_on
     left_off = not left_on
-    ax.axis["bottom"].toggle(ticklabels=bottom_off, label=bottom_off)
-    ax.axis["left"].toggle(ticklabels=left_off, label=left_off)
+
+    # Check if ax.axis supports dict-style access (AxisDict from custom Axes)
+    if hasattr(ax.axis, '__getitem__'):
+        # Custom AxisDict: ax.axis["bottom"] returns a SimpleAxisArtist
+        ax.axis["bottom"].toggle(ticklabels=bottom_off, label=bottom_off)
+        ax.axis["left"].toggle(ticklabels=left_off, label=left_off)
+    else:
+        # ax.axis is a method (default matplotlib Axes, GeoAxes)
+        # Use xaxis/yaxis directly with set_tick_params and set_visible
+        ax.xaxis.set_tick_params(labelbottom=bottom_off)
+        ax.xaxis.label.set_visible(bottom_off)
+        ax.yaxis.set_tick_params(labelleft=left_off)
+        ax.yaxis.label.set_visible(left_off)
 
 
 class CbarAxesBase:
```

## Rules
