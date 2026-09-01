---
name: matplotlib-matplotlib-23964
description: The pytest-all-any-error-messages subject.
subject: matplotlib-matplotlib-23964
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
diff --git a/lib/matplotlib/backends/backend_ps.py b/lib/matplotlib/backends/backend_ps.py
index f209e811f1..bd996b7509 100755
--- a/lib/matplotlib/backends/backend_ps.py
+++ b/lib/matplotlib/backends/backend_ps.py
@@ -666,7 +666,8 @@ grestore
                     (item.x, item.ft_object.get_glyph_name(item.glyph_idx))
                 )
             # append the last entry
-            stream.append(curr_stream)
+            if curr_stream:
+                stream.append(curr_stream)
 
         self.set_color(*gc.get_rgb())
```

## Rules
