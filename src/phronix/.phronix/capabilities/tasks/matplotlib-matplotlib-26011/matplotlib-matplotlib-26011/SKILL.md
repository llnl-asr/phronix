---
name: matplotlib-matplotlib-26011
description: The matplotlib-matplotlib-26011 subject.
subject: matplotlib-matplotlib-26011
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | APPROACH |
| `I3` | Instructions | ANSWER |
| `I4` | Instructions | Guard optional import of _c_internal_utils |
| `I5` | Instructions | Fix set_xlim attribute errors |
| `I6` | Instructions | xlim_changed callback emission on shared axes - pitfalls and lessons |
| `I7` | Instructions | Instructions to solve |
| `I8` | Instructions | xlim_changed callback emission on shared axes - problem statement |
| `R1` | Rules | R1 |
| `R2` | Rules | Constraints and rules |

## Instructions

### I1 — Problem description

The xlim_changed callbacks are not emitted on axes that share limits via `sharex` when the limit change originates from a shared axis, causing test `test_xylim_changed_shared` to fail.

### I2 — APPROACH

Emit `xlim_changed` callbacks on shared axes after syncing limits, and ensure twin axis autoscale flag is copied when sharing limits.

### I3 — ANSWER

In `lib/matplotlib/axes/_base.py` modify `sharex` to call `set_xlim(..., emit=True, ...)` and after updating siblings emit callbacks on each sibling. Also in `sharey` ensure autoscale flag is preserved similarly.

Patch:
```diff
@@
-        self.set_xlim(x0, x1, emit=False, auto=other.get_autoscalex_on())
+        self.set_xlim(x0, x1, emit=True, auto=other.get_autoscalex_on())
@@
-        self.set_ylim(y0, y1, emit=False, auto=other.get_autoscaley_on())
+        self.set_ylim(y0, y1, emit=True, auto=other.get_autoscaley_on())
```

### I4 — Guard optional import of _c_internal_utils

Modify `lib/matplotlib/cbook.py` to import `_c_internal_utils` inside a try/except block:
```python
from matplotlib import _api
try:
    from matplotlib import _c_internal_utils
except ImportError:
    _c_internal_utils = None
```

### I5 — Fix set_xlim attribute errors

Update `set_xlim` in `lib/matplotlib/axes/_base.py` to safely handle missing `_shared_x_axes` and correctly propagate callbacks.

```python
def set_xlim(self, left=None, right=None, emit=True, auto=False):
    if right is not None:
        raise TypeError("Cannot pass both 'right' and 'xmax'")
    if left is not None and isinstance(left, (list, tuple)):
        left, right = left
    # Set limits on this axis
    result = self.xaxis._set_lim(left, right, emit=emit, auto=auto)
    if emit:
        # Process callback for this axis
        self.callbacks.process('xlim_changed', self)
        # Propagate to shared sibling axes if any
        shared = getattr(self, '_shared_x_axes', None)
        if shared is not None:
            for other in shared.get_siblings(self):
                if other is not self:
                    other.callbacks.process('xlim_changed', other)
    return result
```

This avoids AttributeError when `_shared_x_axes` is absent and uses the correct callback mechanism.

**Why:** Previous attempts accessed `_shared_x_axes` directly or assumed it was a dict, causing AttributeError during many tests.

**How to apply:** Replace the existing `set_xlim` implementation with the above code.

### I6 — xlim_changed callback emission on shared axes - pitfalls and lessons

Pitfalls and lessons (from what did not work):
- Moving the callback outside `if emit:` alone was insufficient — the recursion problem persisted because sibling propagation with emit=False still triggers the same code path that leads to infinite recursion
- The recursion error pattern "maximum recursion depth exceeded while calling a Python object" with "same locals & position" indicates the shared axis propagation mechanism itself needs a different approach
- A guard/flag to prevent re-processing of already-processed axes, or changing how shared axis propagation is triggered, may be needed alongside the callback fix
- Setting emit=True on sibling propagation introduces recursion issues, so emit=False must be maintained for the propagation calls

### I7 — Instructions to solve

1. Open `lib/matplotlib/axes/_base.py` at the `set_xlim` method (around line 3643).
2. Replace the original return statement with the new block:
```python
# First set limits on this axis
result = self.xaxis._set_lim(left, right, emit=emit, auto=auto)
# Propagate limit change to shared sibling axes and trigger their callbacks
if emit:
    for other in self._shared_x_axes.get_siblings(self):
        if other is not self:
            other.set_xlim(self.viewLim.intervalx, emit=True, auto=auto)
return result
```

### I8 — xlim_changed callback emission on shared axes - problem statement

The problem: When an axis is shared with another via sharex/=sharey, the registered `xlim_changed`/`ylim_changed` callbacks do not get called when the change is induced by a shared axis. The callback emission `self.axes.callbacks.process(f"{name}lim_changed", self.axes)` was inside the `if emit:` block in `axis.py:_set_lim`, so it only fired when `emit=True` was passed directly. When limits propagate to sibling axes through shared axis mechanisms, the inner calls use `emit=False`, which means the callbacks never fire on those sibling axes.

## Rules

### R1 — R1

Do not alter unrelated behavior; preserve existing passing tests.

### R2 — Constraints and rules

- Do not modify any other parts of `set_xlim` or related logic; only add the propagation block.
- Ensure the change does not introduce recursion; only call `other.set_xlim` with `emit=True` after the primary call.
- The attribute `_shared_x_axes` must exist on the Axes object; the fix assumes it is present as in the original code path.
- All existing regression tests must continue to pass.
- The fix must not alter the behavior when `emit=False` is passed; callbacks should only fire when `emit=True`.

## References
