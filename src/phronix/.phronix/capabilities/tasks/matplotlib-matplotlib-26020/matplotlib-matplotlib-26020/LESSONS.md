# Lessons — matplotlib-matplotlib-26020

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — The symptom a later run would recognise: Creating an AxesGrid with a n

**2026-08-29** — The symptom a later run would recognise: Creating an AxesGrid with a non-default axis_class (like GeoAxes from cartopy) raises TypeError: 'method' object is not subscriptable when trying to access ax.axis["bottom"].

The key insight: ax.axis is a dict-like AxisDict object only on custom Axes subclass in mpl_axes.py. On default matplotlib Axes and GeoAxes, ax.axis is a method (callable), not a property, so subscript access fails. The fix uses duck-typing: check hasattr(ax.axis, '__getitem__') to branch between AxisDict path and xaxis/yaxis method path.

Instructions to solve it (_tick_only function in lib/mpl_toolkits/axes_grid1/axes_grid.py):
1. Capture bottom_off = not bottom_on and left_off = not left_on (lines 14-15)
2. Check if ax.axis supports dict-style access: if hasattr(ax.axis, '__getitem__'): (line 18)
3. If YES (AxisDict case): ax.axis["bottom"].toggle(ticklabels=bottom_off, label=bottom_off); ax.axis["left"].toggle(ticklabels=left_off, label=left_off) (lines 20-21)
4. If NO (method case): ax.xaxis.set_tick_params(labelbottom=bottom_off); ax.xaxis.label.set_visible(bottom_off); ax.yaxis.set_tick_params(labelleft=left_off); ax.yaxis.label.set_visible(left_off) (lines 25-28)
5. The function signature remains: def _tick_only(ax, bottom_on, left_on): (line 13)

Constraints and rules:
- The fix must preserve backward compatibility with AxisDict-based custom Axes (the original working code path)
- The fix must handle the method case for default matplotlib Axes and GeoAxes without raising TypeError
- The hasattr duck-typing check is the single invariant — it must be the first line after computing bottom_off/left_off
- All 48 regression tests must continue passing
- The one target test (GeoAxes with AxesGrid reproduction case) must newly pass
- The fix must not change the function signature or its position in the file
- The comments explaining the two code paths are essential for future maintainability

Pitfalls and lessons:
- Original bug: Directly accessing ax.axis["bottom"] assumes axis is always a dict-like object. This only works for the custom Axes class with AxisDict property. On GeoAxes and default matplotlib Axes, axis is a method (callable), causing TypeError: 'method' object is not subscriptable.
- The fix uses duck-typing (hasattr check) rather than try/except because it's more explicit and readable — the two code paths are fundamentally different, not just error recovery.
- Without the hasattr check, any code passing non-standard axes_class to AxesGrid would crash. The check future-proofs the code against any custom Axes implementation.
- The 48 regression tests confirmed the AxisDict path still works, and the target test confirmed the new method path works for GeoAxes.
