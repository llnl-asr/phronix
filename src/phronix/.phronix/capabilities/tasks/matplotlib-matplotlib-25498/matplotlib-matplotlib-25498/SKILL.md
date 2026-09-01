---
name: matplotlib-matplotlib-25498
description: The matplotlib-ps-fix-lesson subject.
subject: matplotlib-matplotlib-25498
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix Colorbar.update_normal to sync norm and autoscale |
| `I2` | Instructions | Update colorbar after changing norm |
| `I3` | Instructions | Problem solved |
| `I4` | Instructions | Problem it solves |





## Instructions

### I1 — Fix Colorbar.update_normal to sync norm and autoscale

Update `Colorbar.update_normal` to always set the colorbar's `norm` to the mappable's `norm`, then call `autoscale_None` on the norm (if available) to ensure valid `vmin`/`vmax` before resetting the locator/formatter scale. Remove the erroneous `set_cmap` call.

```python
def update_normal(self, mappable):
    """Update the colorbar when the mappable's norm changes.

    This ensures the colorbar's ``norm`` matches the mappable's ``norm`` and
    that the norm has valid ``vmin``/``vmax`` values before the locator and
    formatter are refreshed.
    """
    # Synchronize the norm with the mappable.
    self.norm = getattr(mappable, 'norm', None)
    # Ensure the norm's bounds are initialized.
    if hasattr(self.norm, 'autoscale_None'):
        self.norm.autoscale_None()
    # Refresh the locator/formatter based on the (potentially) new bounds.
    self._reset_locator_formatter_scale()
```

### I2 — Update colorbar after changing norm

After changing the norm of the mappable, call `colorbar.update_normal(mappable)` to refresh the colorbar. Ensure the mappable is passed correctly.

### I3 — Problem solved

Failing Matplotlib colorbar tests due to formatter and scale‑reset regressions.

### I4 — Problem it solves

Failing Matplotlib colorbar tests due to formatter and scale‑reset regressions, e.g. incorrect scientific notation and ValueError on norm reset.

## Rules

## References

- `skill_load(name="matplotlib-ps-fix-lesson", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

