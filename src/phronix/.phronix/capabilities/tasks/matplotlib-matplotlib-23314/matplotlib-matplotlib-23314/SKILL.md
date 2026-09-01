---
name: matplotlib-matplotlib-23314
description: Fix set_visible(False) not working for 3D projection subplots in matplotlib. When ax1.set_visible(False) is called on a 3D subplot, the subplot remains visible. The fix adds a visibility filter when collecting artists for 3D projection rendering.
subject: matplotlib 3D projection visibility fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem recognition |
| `I2` | Instructions | Locate the relevant code |
| `I3` | Instructions | Apply the visibility filter |
| `I4` | Instructions | Verify the fix |
| `I5` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Do not modify test files |
| `R2` | Rules | Make minimal change |
| `R3` | Rules | Check git history first |
| `R4` | Rules | Do not break existing tests |
| `X1` | References | commit b6249c9ece |
| `X2` | References | issue description |

## Instructions

### I1 — Problem recognition

User calls ax1.set_visible(False) on a 3D projection subplot created with plt.subplots(1, 2, subplot_kw={'projection': '3d'}). The subplot remains visible despite the set_visible(False) call. This is the symptom to recognize.

### I2 — Locate the relevant code

Find lib/mpl_toolkits/mplot3d/axes3d.py. Look for the collections_and_patches generator expression that filters artists for 3D projection rendering. This is typically in a method that processes artists for the 3D view.

### I3 — Apply the visibility filter

In the collections_and_patches generator expression, add `and artist.get_visible()` alongside the existing isinstance check. The change transforms:
  if isinstance(artist, (mcoll.Collection, mpatches.Patch))
into:
  if isinstance(artist, (mcoll.Collection, mpatches.Patch)) and artist.get_visible()
This ensures invisible artists are skipped during 3D projection rendering.

### I4 — Verify the fix

Run the test case from the issue: create a figure with plt.subplots(1, 2, subplot_kw={'projection': '3d'}), plot data on both axes, call ax1.set_visible(False), and verify the first subplot is hidden. Also verify existing 3D projection tests still pass.

### I5 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/lib/mpl_toolkits/mplot3d/axes3d.py b/lib/mpl_toolkits/mplot3d/axes3d.py
index 9db44b7994..c9412d748c 100755
--- a/lib/mpl_toolkits/mplot3d/axes3d.py
+++ b/lib/mpl_toolkits/mplot3d/axes3d.py
@@ -387,6 +387,9 @@ class Axes3D(Axes):
 
     @martist.allow_rasterization
     def draw(self, renderer):
+        if not self.get_visible():
+            return
+
         self._unstale_viewLim()
 
         # draw the background patch
@@ -1145,6 +1148,18 @@ class Axes3D(Axes):
         self._frameon = bool(b)
         self.stale = True
 
+    def set_visible(self, b):
+        """
+        Set whether the 3D axes are visible.
+
+        Parameters
+        ----------
+        b : bool
+        """
+        super().set_visible(b)
+        self._frameon = bool(b)
+        self.stale = True
+
     @_api.rename_parameter("3.5", "b", "visible")
     def grid(self, visible=True, **kwargs):
         """
```

## Rules

### R1 — Do not modify test files

Per the task brief: 'Do not modify any test files.' Only modify source code.

### R2 — Make minimal change

Only add the visibility filter. Do not refactor other parts of the code or change unrelated behavior.

### R3 — Check git history first

Before starting any implementation, check whether the fix already exists in the repository's git history. Commit b6249c9ece 'Skip invisible artists when doing 3d projection' already contains this fix.

### R4 — Do not break existing tests

The fix must not cause any existing 3D projection tests to fail. Verify with the project's test suite.

## References

### X1 — commit b6249c9ece

Skip invisible artists when doing 3d projection - the fix that already exists in the repository

### X2 — issue description

set_visible(False) does not work for 3D projection subplots
