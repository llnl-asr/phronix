---
name: scikit-learn-scikit-learn-12471
description: Fix handling of unknown string categories in OneHotEncoder when handle_unknown='ignore'.
subject: scikit-learn-scikit-learn-12471
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Fix steps |
| `I4` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Maintain existing test suite |
| `R2` | Rules | Do not alter handling of numeric categories |

## Instructions

### I1 — Problem description

OneHotEncoder raises ValueError for unknown string categories when handle_unknown='ignore' because it attempts to fill unknown entries with the first known category, causing truncation errors.

### I2 — Key idea

Zeroing out entries for unknown categories is insufficient; the underlying issue is that unknown strings are still processed by _encode, leading to ValueError before the zero‑out can apply.

### I3 — Fix steps

1. In sklearn/preprocessing/_encoders.py, inside _transform, after computing valid_mask, add a guard to skip encoding for unknown categories before calling _encode.
2. Replace the block that sets X_int[~valid_mask, i] = 0 with a conditional that only applies when no unknown string remains after mask.
3. Ensure the function returns X_int and X_mask without invoking _encode on unknown entries.

### I4 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sklearn/preprocessing/_encoders.py b/sklearn/preprocessing/_encoders.py
index 1e05aba59..ec20cd7fd 100755
--- a/sklearn/preprocessing/_encoders.py
+++ b/sklearn/preprocessing/_encoders.py
@@ -111,7 +111,19 @@ class _BaseEncoder(BaseEstimator, TransformerMixin):
                     # removed later.
                     X_mask[:, i] = valid_mask
                     Xi = Xi.copy()
-                    Xi[~valid_mask] = self.categories_[i][0]
+                    # Check if the category value fits in the current dtype,
+                    # and convert to object dtype if necessary (e.g., when
+                    # categories_[i][0] is a longer string than entries in
+                    # the transform data). Fixed-width unicode dtypes will
+                    # silently truncate long strings, so we need to check.
+                    cat_val = self.categories_[i][0]
+                    if Xi.dtype != object and Xi.dtype.kind == 'U':
+                        # Unicode dtype has fixed width; if category value is
+                        # longer, convert to object dtype to preserve it
+                        max_len = Xi.dtype.itemsize // 4  # 4 bytes per char
+                        if len(str(cat_val)) > max_len:
+                            Xi = Xi.astype(object)
+                    Xi[~valid_mask] = cat_val
             _, encoded = _encode(Xi, self.categories_[i], encode=True)
             X_int[:, i] = encoded
```

## Rules

### R1 — Maintain existing test suite

All existing regression tests (53) must continue to pass.

### R2 — Do not alter handling of numeric categories

The fix must only affect string categories; numeric handling should remain unchanged.
