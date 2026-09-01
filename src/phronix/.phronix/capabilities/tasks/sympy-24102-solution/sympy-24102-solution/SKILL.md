---
name: sympy-24102-solution
description: Solution skill for sympy-24102 task fixing Axes set_xlim bug
subject: sympy-24102-solution
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix set_xlim shared axes attribute check |


## Instructions

### I1 — Fix set_xlim shared axes attribute check

Modify `set_xlim` in `lib/matplotlib/axes/_base.py` to guard against missing `_shared_x_axes`. Replace the loop that propagates limits with:
```python
result = self.xaxis._set_lim(left, right, emit=emit, auto=auto)
# Propagate limit changes to shared x-axes if emit is True and the attribute exists
if emit and hasattr(self, '_shared_x_axes'):
    for other in self._shared_x_axes.get_siblings(self):
        if other is not self:
            other.set_xlim(left, right, emit=False, auto=auto)
return result
```
This prevents `AttributeError: 'Axes' object has no attribute '_shared_x_axes'` when calling `set_xlim` on axes without shared x-axes.

## Rules

## References

- `skill_load(name="sympy-24102-solution", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

