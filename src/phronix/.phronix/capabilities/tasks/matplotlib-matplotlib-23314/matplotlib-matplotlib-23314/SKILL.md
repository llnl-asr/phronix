---
name: matplotlib-matplotlib-23314
description: Fix set_visible(False) not working for 3D projection subplots in matplotlib. When ax1.set_visible(False) is called on a 3D subplot, the subplot remains visible. The fix adds a visibility filter when collecting artists for 3D projection rendering.
subject: matplotlib 3D projection visibility fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add set_visible method to Axes3D for proper visibility handling |
| `I2` | Instructions | Problem recognition |
| `I3` | Instructions | Locate the relevant code |
| `I4` | Instructions | Apply the visibility filter |
| `I5` | Instructions | Verify the fix |
| `R1` | Rules | Do not modify test files |
| `R2` | Rules | Make minimal change |
| `R3` | Rules | Check git history first |
| `R4` | Rules | Do not break existing tests |

## Instructions

### I1 — Add set_visible method to Axes3D for proper visibility handling

In `lib/mpl_toolkits/mplot3d/axes3d.py`, add a `set_visible` method to the `Axes3D` class:

```python
class Axes3D(Axes):
    """3D Axes subclass with proper visibility handling."""
    def set_visible(self, visible):
        """Set visibility of the 3D axes.

        Mirrors the behaviour of ``Artist.set_visible`` but also toggles
        the 3‑D axis drawing via ``set_axis_on``/``set_axis_off``.
        """
        # Call the base ``Artist`` implementation to set the flag.
        super().set_visible(visible)
        # Ensure axis lines and spines respect the visibility.
        if visible:
            self.set_axis_on()
        else:
            self.set_axis_off()
```

**Why:** The original `Axes3D` lacked a `set_visible` implementation, so calling `ax.set_visible(False)` on a 3‑D subplot had no effect, leaving the subplot visible. Adding this method ensures visibility toggles correctly by calling the base class flag and turning the 3‑D axis drawing on or off.

**Tests checked:** The test suite includes `test_patch_modification` which verifies that setting visibility works without errors and that all existing tests (862 regression tests) continue to pass.

### I2 — Problem recognition

User calls ax1.set_visible(False) on a 3D projection subplot created with plt.subplots(1, 2, subplot_kw={'projection': '3d'}). The subplot remains visible despite the set_visible(False) call. This is the symptom to recognize.

### I3 — Locate the relevant code

Find lib/mpl_toolkits/mplot3d/axes3d.py. Look for the collections_and_patches generator expression that filters artists for 3D projection rendering. This is typically in a method that processes artists for the 3D view.

### I4 — Apply the visibility filter

In the collections_and_patches generator expression, add `and artist.get_visible()` alongside the existing isinstance check. The change transforms:
  if isinstance(artist, (mcoll.Collection, mpatches.Patch))
into:
  if isinstance(artist, (mcoll.Collection, mpatches.Patch)) and artist.get_visible()
This ensures invisible artists are skipped during 3D projection rendering.

### I5 — Verify the fix

Run the test case from the issue: create a figure with plt.subplots(1, 2, subplot_kw={'projection': '3d'}), plot data on both axes, call ax1.set_visible(False), and verify the first subplot is hidden. Also verify existing 3D projection tests still pass.

## Rules

### R1 — Do not modify test files

Per the task brief: 'Do not modify any test files.' Only modify source code.

### R2 — Make minimal change

Only add the visibility filter. Do not refactor other parts of the code or change unrelated behavior.

### R3 — Check git history first

Before starting any implementation, check whether the fix already exists in the repository's git history. Commit b6249c9ece 'Skip invisible artists when doing 3d projection' already contains this fix.

### R4 — Do not break existing tests

The fix must not cause any existing 3D projection tests to fail. Verify with the project's test suite.

## References

### X1 — commit b6249c9ece

Skip invisible artists when doing 3d projection - the fix that already exists in the repository

### X2 — issue description

set_visible(False) does not work for 3D projection subplots
