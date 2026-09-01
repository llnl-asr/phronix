---
name: scikit-learn-scikit-learn-13439
description: The scikit-learn-scikit-learn-13439 subject.
subject: scikit-learn-scikit-learn-13439
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem recognition for __len__ fix |
| `I2` | Instructions | Key insight about __len__ placement and pattern |
| `I3` | Instructions | Instructions to add __len__ method to Pipeline class |
| `I4` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Constraints and rules for __len__ fix |

## Instructions

### I1 — Problem recognition for __len__ fix

When a user calls `len(pipe)` on a sklearn Pipeline instance and gets `TypeError: object of type 'Pipeline' has no len()`, they need the `__len__` method added to make `len(pipe)` return the number of steps and enable `pipe[:len(pipe)]` slicing to work.

### I2 — Key insight about __len__ placement and pattern

The one insight that the whole fix turns on: `Pipeline` objects support indexing via `__getitem__` (slicing with `[]`) but were missing `__len__`, which Python's sequencing protocol requires for `len()` to work and for slicing patterns like `pipe[:len(pipe)]` to function correctly. The fix is to add `__len__` returning `len(self.steps)` placed immediately after `__getitem__`.

### I3 — Instructions to add __len__ method to Pipeline class

Instructions to solve it: Add a `__len__` method to the `Pipeline` class in `sklearn/pipeline.py`. The method should be placed right after `__getitem__` (before the `_estimator_type` property). The method body is:
```python
def __len__(self):
    """Return the number of steps in the pipeline."""
    return len(self.steps)
```
This is a minimal 3-line addition (including docstring) that makes `len(pipe)` return the number of steps and enables `pipe[:len(pipe)]` to work since `__getitem__` already supports slicing.

### I4 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sklearn/pipeline.py b/sklearn/pipeline.py
index 7eaf9a46f..5efce3e13 100755
--- a/sklearn/pipeline.py
+++ b/sklearn/pipeline.py
@@ -219,6 +219,10 @@ class Pipeline(_BaseComposition):
             return self.named_steps[ind]
         return est
 
+    def __len__(self):
+        """Return the number of steps in the pipeline."""
+        return len(self.steps)
+
     @property
     def _estimator_type(self):
         return self.steps[-1][1]._estimator_type
```

## Rules

### R1 — Constraints and rules for __len__ fix

Constraints and rules:
1. The `__len__` method must be added to the `Pipeline` class in `sklearn/pipeline.py`
2. The method must be placed immediately after `__getitem__` and before the `_estimator_type` property
3. The method must return `len(self.steps)` — the number of steps in the pipeline's steps list
4. A docstring `"""Return the number of steps in the pipeline."""` must be included
5. The change must not modify any test files
6. The change must not alter any existing behavior — only add the `__len__` method
7. The `__len__` method follows Python's protocol: objects supporting `[]` slicing should also support `len()`
8. Verify that all 41 pipeline tests (1 target + 40 regression) pass after the change
