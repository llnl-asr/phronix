---
name: matplotlib-matplotlib-26020
description: Solution skill for fixing axes_grid1 `_tick_only` to work with cartopy GeoAxes
subject: matplotlib-matplotlib-26020
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix _tick_only handling for tuple axis objects |
| `I2` | Instructions | I7 - Naming and Scope |
| `I3` | Instructions | I1 - Problem Summary |
| `I4` | Instructions | I2 - Key Idea |





## Instructions

### I1 — Fix _tick_only handling for tuple axis objects

Update the `_tick_only` helper in `lib/mpl_toolkits/axes_grid1/axes_grid.py` to correctly handle `Axes` objects whose `axis` attribute returns a tuple (as with `cartopy.geoaxes.GeoAxes`). The new implementation checks if `ax.axis` is callable, calls it, and then determines whether the result is a mapping (dict‑like) or a tuple. For a tuple, it unpacks the bottom and left axis objects accordingly before toggling tick labels and axis labels.
```python
def _tick_only(ax, bottom_on, left_on):
    bottom_off = not bottom_on
    left_off = not left_on
    # Resolve the axis container: callable, dict‑like, or tuple
    axis_container = ax.axis() if callable(getattr(ax, "axis", None)) else ax.axis
    if isinstance(axis_container, tuple):
        # cartopy GeoAxes returns (xaxis, yaxis)
        bottom_axis, left_axis = axis_container
    else:
        bottom_axis = axis_container["bottom"]
        left_axis = axis_container["left"]
    bottom_axis.toggle(ticklabels=bottom_off, label=bottom_off)
    left_axis.toggle(ticklabels=left_off, label=left_off)
```

### I2 — I7 - Naming and Scope

Name the skill after the repository and issue ID: `matplotlib-matplotlib-26020`. This skill contains the fix for handling both dict-like and callable `axis` attributes in `AxesGrid`.

I9 - What belongs in a skill rather than a memory

### I3 — I1 - Problem Summary

A later run sees a failing test `test_grid_with_axes_class_not_overriding_axis` caused by `AxesGrid` when `axis` attribute of a Cartopy `GeoAxes` is a callable, not a dict. The code attempts `ax.axis["bottom"]` leading to `TypeError: 'method' object is not subscriptable` and further tuple index errors.

### I4 — I2 - Key Idea

Detect whether `ax.axis` is callable; if so, call it to obtain the dict-like object before indexing. This unifies handling of both dict-like and callable `axis` attributes.

## Rules

## References

- `skill_load(name="matplotlib-26020-solution", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

