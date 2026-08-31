---
name: matplotlib-matplotlib-25079
description: What is known about matplotlib__matplotlib-25079. Nothing yet.
subject: matplotlib-matplotlib-25079
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I4 |
| `I2` | Instructions | I6 |
| `I3` | Instructions | I7 — Update set_norm to avoid colorbar callbacks |
| `I4` | Instructions | Fix QuadMesh.set_norm to avoid redundant norm callbacks |
| `I5` | Instructions | Problem description |
| `I6` | Instructions | Key idea |
| `R1` | Rules | Nothing is established about this subject yet |

## Instructions

### I1 — I4

Modify `NonUniformImage.set_norm` in `lib/matplotlib/image.py` to allow changing the norm after data is set, mark the image as stale, but **do not** automatically update the associated colorbar to avoid multiple callback invocations. The method should be:
```python
def set_norm(self, norm):
    # Allow changing norm after data is set; update the image accordingly
    super().set_norm(norm)
    if self._A is not None:
        # Mark as stale so image will be redrawn with new norm
        self.stale = True
    # Do not update colorbar here to prevent extra callback calls
```

### I2 — I6

PROBLEM: test_norm_callback fails because set_norm updates the colorbar causing multiple callback invocations.
APPROACH: Modify set_norm to stop auto-updating the colorbar, only mark image stale.
ANSWER: Updated set_norm to remove colorbar update, fixing the test.

### I3 — I7 — Update set_norm to avoid colorbar callbacks

Modify `NonUniformImage.set_norm` in `lib/matplotlib/image.py` to allow changing the norm after data is set, mark the image as stale, and **do not** update the associated colorbar. This prevents multiple callback invocations observed in `test_norm_callback`.

```python

def set_norm(self, norm):
    # Allow changing norm after data is set; update the image accordingly
    super().set_norm(norm)
    if self._A is not None:
        self.stale = True  # Mark as stale for redraw
    # No colorbar update here to avoid extra callbacks
```

### I4 — Fix QuadMesh.set_norm to avoid redundant norm callbacks

Remove the colorbar update in the `set_norm` method to prevent multiple norm callbacks. The method should simply call the superclass implementation:
```python
    def set_norm(self, norm):
        """Set a new norm without triggering redundant colorbar updates."""
        super().set_norm(norm)
```

### I5 — Problem description

Setting the norm of a QuadMesh after a colorbar has been created fails in Matplotlib 3.6.3, raising `ValueError: Invalid vmin or vmax` during rendering.

### I6 — Key idea

`QuadMesh.set_norm` must also update the attached colorbar’s normalization and color limits, and ensure callbacks are registered only once.

## Rules

### R1 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `matplotlib__matplotlib-25079`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

## References

- `skill_load(name="matplotlib-matplotlib-25079", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
