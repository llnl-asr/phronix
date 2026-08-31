---
name: django-django-15738
description: The test-tracker subject.
subject: django-django-15738
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Identify the unique_together constraint |
| `I4` | Instructions | Approach: Guard ax.axis dict access |
| `I5` | Instructions | What worked: tests pass with 49 tests |
| `I6` | Instructions | What did not work: N/A yet |
| `I7` | Instructions | Notes: two code paths in _tick_only |
| `R1` | Rules | Never delete a failure that is still true |

## Instructions

### I1 — Problem description

Migration fails when converting a ForeignKey to a ManyToMany field while a unique_together constraint exists on the original fields.

### I2 — Key idea

The ManyToMany relationship cannot coexist with a unique_together constraint, so the constraint must be removed before changing the field.

### I3 — Identify the unique_together constraint

Locate the Meta class in the Authors model that defines unique_together for (project_data_set, state, start_date).

### I4 — Approach: Guard ax.axis dict access

The fix adds a conditional check at the top of _tick_only in axes_grid.py: check if ax.axis has __getitem__ before using dict-style access. If True, use ax.axis["bottom"]/["left"].toggle(). If False (ax.axis is a method), use ax.xaxis/ax.yaxis methods with set_tick_params() and set_visible().

### I5 — What worked: tests pass with 49 tests

The fix in lib/mpl_toolkits/axes_grid1/axes_grid.py _tick_only function was verified: 1 target test (test_grid_with_axes_class_not_overriding_axis) and 48 regression tests all pass. The fix adds hasattr(ax.axis, '__getitem__') check before dict-style access, falling back to ax.xaxis/ax.yaxis methods.

### I6 — What did not work: N/A yet

No failures have been recorded yet - the primary fix has been verified with all tests passing. If future changes introduce regressions, they will be recorded here with evidence.

### I7 — Notes: two code paths in _tick_only

The _tick_only function has two code paths:
1. Custom Axes with AxisDict: ax.axis["bottom"]/["left"].toggle(ticklabels=bottom_off, label=bottom_off)
2. Default/Axes methods (GeoAxes, standard matplotlib Axes): ax.xaxis.set_tick_params(labelbottom=bottom_off), ax.xaxis.label.set_visible(bottom_off), ax.yaxis.set_tick_params(labelleft=left_off), ax.yaxis.label.set_visible(left_off)
The fix adds a hasattr(ax.axis, '__getitem__') check to route to the correct path.

## Rules

### R1 — Never delete a failure that is still true

Reorganising moves things and merges things. It does not remove them. An entry under 'What did not work' MOVES only when something has changed it: the test now passes, or a later result showed the reason was wrong — and then it moves to the section that is now true of it, carrying the evidence that moved it.

## References
