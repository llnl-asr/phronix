---
name: matplotlib-matplotlib-25442
description: The matplotlib-matplotlib-25442 subject.
subject: matplotlib-matplotlib-25442
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix _check_still_parented None guard |
| `I2` | Instructions | Fix disconnect method None guard |
| `I3` | Instructions | Fix for mplcursor AttributeError with matplotlib 3.7.1 |
| `I4` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Fix _check_still_parented None guard

When fixing _check_still_parented in matplotlib's offsetbox.py, add `self.ref_artist is not None` guard before accessing `.figure`:

```python
def _check_still_parented(self):
    if self.ref_artist is not None and self.ref_artist.figure is None:
        self.disconnect()
        return False
    elif self.ref_artist is None:
        return False
    else:
        return True
```

This prevents AttributeError when self.ref_artist has been garbage collected or removed.

### I2 — Fix disconnect method None guard

When fixing disconnect() in matplotlib's offsetbox.py, guard the entire method body with `self.ref_artist is not None and self.ref_artist.figure is not None` before accessing the canvas property:

```python
def disconnect(self):
    """Disconnect the callbacks."""
    if self.ref_artist is not None and self.ref_artist.figure is not None:
        for cid in self.cids:
            self.canvas.mpl_disconnect(cid)
        try:
            c1 = self._c1
        except AttributeError:
            pass
        else:
            self.canvas.mpl_disconnect(c1)
```

This prevents AttributeError: 'NoneType' object has no attribute 'canvas' when the artist has been detached from its figure.

### I3 — Fix for mplcursor AttributeError with matplotlib 3.7.1



### I4 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/lib/matplotlib/offsetbox.py b/lib/matplotlib/offsetbox.py
index 77768e7383..f98544b507 100755
--- a/lib/matplotlib/offsetbox.py
+++ b/lib/matplotlib/offsetbox.py
@@ -1550,22 +1550,25 @@ class DraggableBase:
                 self.ref_artist.set_animated(False)
 
     def _check_still_parented(self):
-        if self.ref_artist.figure is None:
+        if self.ref_artist is not None and self.ref_artist.figure is None:
             self.disconnect()
             return False
+        elif self.ref_artist is None:
+            return False
         else:
             return True
 
     def disconnect(self):
         """Disconnect the callbacks."""
-        for cid in self.cids:
-            self.canvas.mpl_disconnect(cid)
-        try:
-            c1 = self._c1
-        except AttributeError:
-            pass
-        else:
-            self.canvas.mpl_disconnect(c1)
+        if self.ref_artist is not None and self.ref_artist.figure is not None:
+            for cid in self.cids:
+                self.canvas.mpl_disconnect(cid)
+            try:
+                c1 = self._c1
+            except AttributeError:
+                pass
+            else:
+                self.canvas.mpl_disconnect(c1)
 
     def save_offset(self):
         pass
```

## Rules
