---
name: scikit-learn-scikit-learn-11040
description: The scikit-learn-scikit-learn-11040 subject.
subject: scikit-learn-scikit-learn-11040
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Validate n_neighbors as integer in both constructor and kneighbors |


## Instructions

### I1 — Validate n_neighbors as integer in both constructor and kneighbors

Add integer type check for `n_neighbors` in `NeighborsBase.__init__` **and** in the `kneighbors` method of relevant estimators. Raise a clear `ValueError` if a float is provided.

```diff
@@
-        self.n_neighbors = n_neighbors
-        if self.n_neighbors is not None and not isinstance(self.n_neighbors, (int, np.integer)):
-            raise ValueError("n_neighbors must be an integer, got %s" % type(self.n_neighbors))
+        self.n_neighbors = n_neighbors
+        if self.n_neighbors is not None and not isinstance(self.n_neighbors, (int, np.integer)):
+            raise ValueError("n_neighbors must be an integer, got %s" % type(self.n_neighbors))
@@
 def kneighbors(self, X=None, n_neighbors=None, return_distance=True):
+    if n_neighbors is not None and not isinstance(n_neighbors, (int, np.integer)):
+        raise ValueError("n_neighbors must be an integer, got %s" % type(n_neighbors))
```

## Rules

## References
