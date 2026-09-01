---
name: matplotlib-matplotlib-26011
description: The matplotlib-matplotlib-26011 subject.
subject: matplotlib-matplotlib-26011
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | xlim_changed callback emission on shared axes - problem statement |
| `I2` | Instructions | xlim_changed callback emission on shared axes - key idea |
| `I3` | Instructions | xlim_changed callback emission on shared axes - the change |
| `I4` | Instructions | xlim_changed callback emission on shared axes - constraints and rules |
| `I5` | Instructions | xlim_changed callback emission on shared axes - pitfalls and lessons |






## Instructions

### I1 — xlim_changed callback emission on shared axes - problem statement

The problem: When an axis is shared with another via sharex/=sharey, the registered `xlim_changed`/`ylim_changed` callbacks do not get called when the change is induced by a shared axis. The callback emission `self.axes.callbacks.process(f"{name}lim_changed", self.axes)` was inside the `if emit:` block in `axis.py:_set_lim`, so it only fired when `emit=True` was passed directly. When limits propagate to sibling axes through shared axis mechanisms, the inner calls use `emit=False`, which means the callbacks never fire on those sibling axes.

### I2 — xlim_changed callback emission on shared axes - key idea

The key idea: Moving the callback invocation outside the `if emit:` block ensures the callback always fires on the originating axis, while keeping `emit=False` for the sibling propagation prevents recursion issues (as the issue reporter noted: "Setting emit=True seems to introduce a recursion issue"). The fix trades recursion risk for callback coverage — callbacks now fire on the original axis regardless of how the change propagates, but sibling axes still use emit=False to avoid infinite recursion loops.

### I3 — xlim_changed callback emission on shared axes - the change

The change (in `lib/matplotlib/axis.py:_set_lim`):
- Moved `self.axes.callbacks.process(f"{name}lim_changed", self.axes)` outside the `if emit:` block, so it executes unconditionally
- Kept the sibling axis propagation with `emit=False` to prevent recursion, as removing it causes even more test failures
- The callback now fires on the original axis even when limit changes propagate through shared axes, but sibling axes still use emit=False to avoid recursion loops

### I4 — xlim_changed callback emission on shared axes - constraints and rules

Constraints and rules:
- Must keep `emit=False` for sibling axis propagation (removing it causes 47+ additional test failures due to recursion)
- Callback must fire on the originating axis regardless of emit setting
- The fix addresses the core issue: xlim_changed/ylim_changed callbacks now fire even when limit changes propagate through shared axes
- Do not modify any test files; only edit source code

### I5 — xlim_changed callback emission on shared axes - pitfalls and lessons

Pitfalls and lessons (from what did not work):
- Moving the callback outside `if emit:` alone was insufficient — the recursion problem persisted because sibling propagation with emit=False still triggers the same code path that leads to infinite recursion
- The recursion error pattern "maximum recursion depth exceeded while calling a Python object" with "same locals & position" indicates the shared axis propagation mechanism itself needs a different approach
- A guard/flag to prevent re-processing of already-processed axes, or changing how shared axis propagation is triggered, may be needed alongside the callback fix
- Setting emit=True on sibling propagation introduces recursion issues, so emit=False must be maintained for the propagation calls

## Rules

## References
