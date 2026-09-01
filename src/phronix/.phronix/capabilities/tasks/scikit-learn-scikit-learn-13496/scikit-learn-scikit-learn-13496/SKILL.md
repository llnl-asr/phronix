---
name: scikit-learn-scikit-learn-13496
description: The scikit-learn-scikit-learn-13496 subject.
subject: scikit-learn-scikit-learn-13496
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Expose warm_start in IsolationForest.__init__ — problem & solution |
| `I2` | Instructions | Constraints and rules for warm_start exposure |
| `I3` | Instructions | Pitfalls and lessons for warm_start exposure |
| `I4` | Instructions | Key idea: warm_start exposed in constructor |
| `I5` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — Expose warm_start in IsolationForest.__init__ — problem & solution

Problem: IsolationForest supports warm_start inherited from BaseBagging for incremental training but it's not exposed in __init__(). Users must set it post-init and manually increment n_estimators.

Solution: Expose warm_start parameter in IsolationForest.__init__() with default=False, making incremental training accessible through the constructor.

### I2 — Constraints and rules for warm_start exposure

warm_start must default to False for backward compatibility. Existing 19 regression tests must keep passing. Only modify iforest.py — no test files. Parameter must pass through to BaseBagging.__init__() via super().__init__().

### I3 — Pitfalls and lessons for warm_start exposure

Initially parameter was not visible in __init__() despite inheritance from BaseBagging — required inspecting source of both IsolationForest and BaseBagging. warm_start=True requires incrementing n_estimators on each iteration for incremental training. Fix is minimal (2 lines) but easy to miss if not examining constructor signature.

### I4 — Key idea: warm_start exposed in constructor

Expose warm_start parameter in IsolationForest.__init__() with default=False, making incremental training accessible directly through the constructor — same pattern as RandomForestClassifier.

### I5 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sklearn/ensemble/iforest.py b/sklearn/ensemble/iforest.py
index 8a1bd3625..20fc0d803 100755
--- a/sklearn/ensemble/iforest.py
+++ b/sklearn/ensemble/iforest.py
@@ -173,7 +173,8 @@ class IsolationForest(BaseBagging, OutlierMixin):
                  n_jobs=None,
                  behaviour='old',
                  random_state=None,
-                 verbose=0):
+                 verbose=0,
+                 warm_start=False):
         super().__init__(
             base_estimator=ExtraTreeRegressor(
                 max_features=1,
@@ -187,7 +188,8 @@ class IsolationForest(BaseBagging, OutlierMixin):
             max_features=max_features,
             n_jobs=n_jobs,
             random_state=random_state,
-            verbose=verbose)
+            verbose=verbose,
+            warm_start=warm_start)
 
         self.behaviour = behaviour
         self.contamination = contamination
```

## Rules
