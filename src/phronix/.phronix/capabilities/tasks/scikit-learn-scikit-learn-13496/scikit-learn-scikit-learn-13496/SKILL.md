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
| `I2` | Instructions | Problem description |
| `I3` | Instructions | Key idea: warm_start exposed in constructor |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | Constraints and rules for warm_start exposure |
| `I6` | Instructions | Pitfalls and lessons for warm_start exposure |
| `R1` | Rules | Constraints |

## Instructions

### I1 — Expose warm_start in IsolationForest.__init__ — problem & solution

Problem: IsolationForest supports warm_start inherited from BaseBagging for incremental training but it's not exposed in __init__(). Users must set it post-init and manually increment n_estimators.

Solution: Expose warm_start parameter in IsolationForest.__init__() with default=False, making incremental training accessible through the constructor.

### I2 — Problem description

IsolationForest lacks an exposed `warm_start` parameter in its `__init__`, causing tests that require warm start functionality to fail.

### I3 — Key idea: warm_start exposed in constructor

Expose warm_start parameter in IsolationForest.__init__() with default=False, making incremental training accessible directly through the constructor — same pattern as RandomForestClassifier.

### I4 — Instructions to solve it

1. Open `sklearn/ensemble/iforest.py`.
2. Locate the `IsolationForest` class definition and its `__init__` signature.
3. Add a new parameter `warm_start=False` after `random_state=None` (preserving existing ordering).
4. Ensure the call to `super().__init__` passes through this argument via `**kwargs` or explicit `warm_start=warm_start` if required.
5. Update the docstring of `IsolationForest.__init__` to document the new parameter, mirroring the description used in `RandomForestClassifier`.
6. Add a test in `sklearn/ensemble/tests/test_iforest.py` that sets `warm_start=True`, fits the model twice with increased `n_estimators`, and asserts that the second fit reuses the first estimator.
7. Run the relevant test `test_iforest_warm_start` to verify the fix.

### I5 — Constraints and rules for warm_start exposure

warm_start must default to False for backward compatibility. Existing 19 regression tests must keep passing. Only modify iforest.py — no test files. Parameter must pass through to BaseBagging.__init__() via super().__init__().

### I6 — Pitfalls and lessons for warm_start exposure

Initially parameter was not visible in __init__() despite inheritance from BaseBagging — required inspecting source of both IsolationForest and BaseBagging. warm_start=True requires incrementing n_estimators on each iteration for incremental training. Fix is minimal (2 lines) but easy to miss if not examining constructor signature.

## Rules

### R1 — Constraints

- Must not alter the behavior of IsolationForest when `warm_start=False` (default) – existing functionality must remain unchanged.
- All existing regression tests (19) must continue to pass.
- The new parameter should be passed to the BaseBagging initializer without breaking other arguments.
- Documentation updates must match scikit‑learn style guidelines.

## References
