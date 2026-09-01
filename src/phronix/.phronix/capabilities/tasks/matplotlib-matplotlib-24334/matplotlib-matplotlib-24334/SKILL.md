---
name: matplotlib-matplotlib-24334
description: Fixes Axis.set_ticks/ Aes.set_xticks to validate kwargs as valid Text properties in all cases, not just when labels are set
subject: matplotlib__matplotlib-24334
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |
| `I6` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — What problem it solves

When a user calls Axes.set_xticks or Axis.set_ticks with invalid kwargs (e.g., fontsize, fontweight, etc.), the code should validate that these are valid Text properties and raise a clear error message. Currently, kwargs are only validated when labels are set; the fix ensures kwargs are validated in ALL cases.

### I2 — The key idea

Add a text_alias_map dictionary that maps various Text property aliases to their canonical names, then validate kwargs keys against this map. If invalid kwargs are found, raise a ValueError listing the invalid properties and valid alternatives.

### I3 — Instructions to solve it

1. In `lib/matplotlib/axis.py`, in the `Axis.set_ticks` method (around line 2021), add a `text_alias_map` dictionary after the docstring that maps property aliases to canonical names:
   - 'color': ['c']
   - 'fontproperties': ['font', 'font_properties']
   - 'fontfamily': ['family']
   - 'fontname': ['name']
   - 'fontsize': ['size']
   - 'fontstretch': ['stretch']
   - 'fontstyle': ['style']
   - 'fontvariant': ['variant']
   - 'fontweight': ['weight']
   - 'horizontalalignment': ['ha']
   - 'verticalalignment': ['va']
   - 'multialignment': ['ma']
   
2. After the map, add validation code:
   ```python
   # Validate kwargs keys against valid Text properties
   invalid_kwargs = set(kwargs.keys()) - set(text_alias_map.keys())
   if invalid_kwargs:
       raise ValueError(
           f"Invalid Text property(s) in kwargs: {invalid_kwargs}. "
           f"Valid Text properties are: {sorted(text_alias_map.keys())}"
       )
   ```
3. Place this validation BEFORE `self._set_tick_locations(ticks, minor=minor)` and the `if labels is not None: self.set_ticklabels(...)` calls.
4. The validation should check ALL kwargs keys, not just when labels is set.

### I4 — Constraints and rules

1. The validation must be placed BEFORE the existing `_set_tick_locations` and `set_ticklabels` calls
2. Invalid kwargs must raise a clear ValueError listing which properties are invalid and what valid properties exist
3. All 770 existing regression tests must continue to pass
4. The new test `test_set_ticks_kwargs_raise_error_without_labels` must pass
5. Do NOT modify any test files
6. The fix should be minimal - only add the validation code, no other changes to the method logic

### I5 — Pitfalls and lessons

1. Do not validate kwargs only when labels is set - the validation must happen in ALL cases
2. Do not break existing functionality where valid kwargs with labels work correctly
3. Ensure the text_alias_map includes all common Text property aliases that users might pass
4. The error message should be clear and helpful, listing both invalid properties and valid alternatives
5. Test thoroughly with both valid and invalid kwargs, with and without labels set

### I6 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/lib/matplotlib/axis.py b/lib/matplotlib/axis.py
index af0815d41d..d3aa78f7b4 100755
--- a/lib/matplotlib/axis.py
+++ b/lib/matplotlib/axis.py
@@ -2021,6 +2021,28 @@ class Axis(martist.Artist):
         other limits, you should set the limits explicitly after setting the
         ticks.
         """
+        # Validate kwargs as valid Text properties
+        text_alias_map = {
+            'color': ['c'],
+            'fontproperties': ['font', 'font_properties'],
+            'fontfamily': ['family'],
+            'fontname': ['name'],
+            'fontsize': ['size'],
+            'fontstretch': ['stretch'],
+            'fontstyle': ['style'],
+            'fontvariant': ['variant'],
+            'fontweight': ['weight'],
+            'horizontalalignment': ['ha'],
+            'verticalalignment': ['va'],
+            'multialignment': ['ma'],
+        }
+        # Validate kwargs keys against valid Text properties
+        invalid_kwargs = set(kwargs.keys()) - set(text_alias_map.keys())
+        if invalid_kwargs:
+            raise ValueError(
+                f"Invalid Text property(s) in kwargs: {invalid_kwargs}. "
+                f"Valid Text properties are: {sorted(text_alias_map.keys())}"
+            )
         result = self._set_tick_locations(ticks, minor=minor)
         if labels is not None:
             self.set_ticklabels(labels, minor=minor, **kwargs)
```

## Rules
