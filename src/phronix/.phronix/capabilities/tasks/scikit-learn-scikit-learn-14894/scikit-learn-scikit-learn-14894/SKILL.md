---
name: scikit-learn-scikit-learn-14894
description: The scikit-learn-scikit-learn-14894 subject.
subject: scikit-learn-scikit-learn-14894
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
diff --git a/sklearn/svm/base.py b/sklearn/svm/base.py
index 64cebe837..9a8a49a16 100755
--- a/sklearn/svm/base.py
+++ b/sklearn/svm/base.py
@@ -286,12 +286,17 @@ class BaseLibSVM(BaseEstimator, metaclass=ABCMeta):
             n_class = 1
         n_SV = self.support_vectors_.shape[0]
 
-        dual_coef_indices = np.tile(np.arange(n_SV), n_class)
-        dual_coef_indptr = np.arange(0, dual_coef_indices.size + 1,
-                                     dual_coef_indices.size / n_class)
-        self.dual_coef_ = sp.csr_matrix(
-            (dual_coef_data, dual_coef_indices, dual_coef_indptr),
-            (n_class, n_SV))
+        # Handle case with no support vectors to avoid division by zero
+        if n_SV == 0:
+            # Empty dual coefficients matrix with appropriate shape
+            self.dual_coef_ = sp.csr_matrix((n_class, 0))
+        else:
+            dual_coef_indices = np.tile(np.arange(n_SV), n_class)
+            dual_coef_indptr = np.arange(0, dual_coef_indices.size + 1,
+                                         dual_coef_indices.size / n_class)
+            self.dual_coef_ = sp.csr_matrix(
+                (dual_coef_data, dual_coef_indices, dual_coef_indptr),
+                (n_class, n_SV))
 
     def predict(self, X):
         """Perform regression on samples in X.
```

## Rules
