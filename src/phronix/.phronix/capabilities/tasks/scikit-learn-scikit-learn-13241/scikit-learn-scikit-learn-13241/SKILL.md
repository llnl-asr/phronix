---
name: scikit-learn-scikit-learn-13241
description: The test-tracker subject.
subject: scikit-learn-scikit-learn-13241
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Task completion: fix verified |


## Instructions

### I1 — Task completion: fix verified

The fix in lib/mpl_toolkits/axes_grid1/axes_grid.py _tick_only function has been verified: 1 target test (test_grid_with_axes_class_not_overriding_axis) and 48 regression tests all pass. The conditional check `hasattr(ax.axis, '__getitem__')` routes to the correct code path for both custom Axes with AxisDict and default/GeoAxes where axis is a method.

## Rules

## References
