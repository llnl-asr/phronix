---
name: scikit-learn-scikit-learn-13439
description: The scikit-learn-scikit-learn-13439 subject.
subject: scikit-learn-scikit-learn-13439
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Instructions to add __len__ method to Pipeline class |
| `I2` | Instructions | Problem recognition for __len__ fix |
| `I3` | Instructions | Key insight about __len__ placement and pattern |
| `R1` | Rules | Maintain existing behavior |
| `R2` | Rules | Constraints and rules for __len__ fix |

## Instructions

### I1 — Instructions to add __len__ method to Pipeline class

Instructions to solve it: Add a `__len__` method to the `Pipeline` class in `sklearn/pipeline.py`. The method should be placed right after `__getitem__` (before the `_estimator_type` property). The method body is:
```python
def __len__(self):
    """Return the number of steps in the pipeline."""
    return len(self.steps)
```
This is a minimal 3-line addition (including docstring) that makes `len(pipe)` return the number of steps and enables `pipe[:len(pipe)]` to work since `__getitem__` already supports slicing.

### I2 — Problem recognition for __len__ fix

When a user calls `len(pipe)` on a sklearn Pipeline instance and gets `TypeError: object of type 'Pipeline' has no len()`, they need the `__len__` method added to make `len(pipe)` return the number of steps and enable `pipe[:len(pipe)]` slicing to work.

### I3 — Key insight about __len__ placement and pattern

The one insight that the whole fix turns on: `Pipeline` objects support indexing via `__getitem__` (slicing with `[]`) but were missing `__len__`, which Python's sequencing protocol requires for `len()` to work and for slicing patterns like `pipe[:len(pipe)]` to function correctly. The fix is to add `__len__` returning `len(self.steps)` placed immediately after `__getitem__`.

## Rules

### R1 — Maintain existing behavior

The added method must not alter any existing functionality of `Pipeline`. All existing regression tests (40) must continue to pass.

### R2 — Constraints and rules for __len__ fix

Constraints and rules:
1. The `__len__` method must be added to the `Pipeline` class in `sklearn/pipeline.py`
2. The method must be placed immediately after `__getitem__` and before the `_estimator_type` property
3. The method must return `len(self.steps)` — the number of steps in the pipeline's steps list
4. A docstring `"""Return the number of steps in the pipeline."""` must be included
5. The change must not modify any test files
6. The change must not alter any existing behavior — only add the `__len__` method
7. The `__len__` method follows Python's protocol: objects supporting `[]` slicing should also support `len()`
8. Verify that all 41 pipeline tests (1 target + 40 regression) pass after the change

## References

- `skill_load(name="scikit-learn-scikit-learn-13439", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
