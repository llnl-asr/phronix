---
name: matplotlib-matplotlib-25311
description: The matplotlib-matplotlib-25311 subject.
subject: matplotlib-matplotlib-25311
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix Figure.__setstate__ to avoid canvas pickling |
| `I2` | Instructions | Problem description |
| `I3` | Instructions | Problem identification (symptom) |
| `I4` | Instructions | Key idea |
| `I5` | Instructions | Steps to solve |
| `I6` | Instructions | Diagnosis for matplotlib issue 25311 |

## Instructions

### I1 — Fix Figure.__setstate__ to avoid canvas pickling

Update `Figure.__setstate__` in `lib/matplotlib/figure.py` to fully remove canvas references after popping the `canvas` entry. After `state.pop("canvas")`, also clear any lingering canvas attribute to prevent it from being pickled:
```python
# Discard canvas reference to avoid pickling it
state.pop("canvas", None)
if hasattr(self, "canvas"):
    del self.canvas
```
This ensures `FigureCanvasAgg` is not present in the pickle operations, satisfying `test_complete[png]`.

### I2 — Problem description

Pickling a Figure containing a draggable legend fails because the draggable legend holds references to the canvas, causing an AssertionError that 'FigureCanvasAgg' appears in the pickle.

### I3 — Problem identification (symptom)

A test fails: `lib/matplotlib/tests/test_pickle.py::test_complete[png]` asserts that the pickle of a Figure does not contain the string "FigureCanvasAgg". With a draggable legend, the pickle includes this canvas, causing the assertion to fail.

### I4 — Key idea

Clear the `_draggable` attribute of each legend in the Figure during unpickling to break the reference to the canvas.

### I5 — Steps to solve

1. Open `lib/matplotlib/figure.py`.
2. Locate the `Figure.__setstate__` method.
3. After `state.pop("canvas")`, insert the following code to clear draggable legends:
```
for leg in getattr(self, "legends", []):
    if getattr(leg, "_draggable", None) is not None:
        leg._draggable = None
```
4. Save the file.
5. Run the target test `lib/matplotlib/tests/test_pickle.py::test_complete[png]` to verify the assertion no longer finds "FigureCanvasAgg" in the pickle.
6. Run the full regression test suite to ensure no new failures are introduced.

### I6 — Diagnosis for matplotlib issue 25311

Task: matplotlib-matplotlib-25311

This is a SWE-bench task involving matplotlib issue #25311. The issue requires fixing a bug in the matplotlib repository.

Key aspects identified from task context:
- This is a checked-out matplotlib repository that needs modification
- The fix should address the specific issue described in the task brief
- Tests should be run to verify the fix, focusing on tests related to the changed code area
- The fix should be minimal - only the necessary changes to fix the issue
- Do not modify test files
- Any failing test outside the touched area was likely pre-existing and should not be chased

The task involves working in a git repository with the code checked out. The issue number 25311 refers to a specific bug or feature in matplotlib that needs to be addressed through code changes following the standard SWE-bench methodology: diagnose the issue, make minimal code changes, verify with targeted tests, and ensure the fix resolves the reported problem without introducing unrelated changes.

This diagnosis was recorded to guide the next attempt at this task, ensuring continuity of understanding about the issue nature and the approach needed.

## References
