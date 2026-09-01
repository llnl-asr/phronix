---
name: matplotlib-matplotlib-22711
description: The matplotlib-matplotlib-22711 subject.
subject: matplotlib-matplotlib-22711
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Constraints and rules |






## Instructions

### I1 — What problem it solves

The symptom is IndexError: index 4 is out of bounds for axis 0 with size 4 that occurs when creating a RangeSlider widget with valinit=[0.0, 0.0] (or any initialization that results in the polygon having only 4 elements). The code in set_val tries to access xy[4], but self.poly.xy only has 4 elements (indices 0-3), causing the error. This prevents RangeSlider from being initialized at all.

### I2 — The key idea

The xy[4] assignment in RangeSlider.set_val assumes the polygon has 5 vertices, but self.poly.xy (from axhspan/axvspan) only provides 4 vertices for a rectangular patch. The 0.25 value at xy[4] represents the handle height proportion, but it cannot be set at index 4 because the array only has 4 elements (a rectangle has vertices at indices 0-3).

### I3 — Instructions to solve it

File: lib/matplotlib/widgets.py
1. Line 906: Comment out xy[4] = .25, val[0] (vertical orientation) → # xy[4] = .25, val[0]
2. Line 912: Comment out xy[4] = val[0], .25 (horizontal orientation) → # xy[4] = val[0], .25

### I4 — Pitfalls and lessons

- Attempt 1: Commenting out xy[4] lines fixes the IndexERROR but causes test failures because tests expect 0.25 in polygon point coordinates
- Attempt 2: Same as Attempt 1 - identical results (0 of 2 target tests passed, 91 of 91 regression tests passed)
- Attempt 3: Same fix, plus test_rectangle_selector also fails (3 failed total: 2 range_slider tests + 1 rectangle_selector test)
- The "comment out xy[4]" approach is definitively exhausted across 3 attempts - all produced identical results: 0 of 2 target tests passed despite 91 of 91 regression tests passing
- Next phase should explore alternative fixes: modify polygon initialization to ensure xy always has 5 elements, use conditional logic to check xy.shape[0] before accessing xy[4], or investigate different code path for polygon creation/update

## Rules

### R1 — Constraints and rules

- 91 of 91 regression tests must continue to pass
- Do not modify test files
- The fix must prevent the IndexError without breaking existing functionality
- The polygon xy array has only 4 elements (a rectangle has 4 vertices at indices 0-3)
- The fix comments out the xy[4] = ... assignments that assume 5 vertices

## References
