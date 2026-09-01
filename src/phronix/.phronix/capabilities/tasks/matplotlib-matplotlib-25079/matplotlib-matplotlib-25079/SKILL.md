---
name: matplotlib-matplotlib-25079
description: What is known about matplotlib__matplotlib-25079. Nothing yet.
subject: matplotlib-matplotlib-25079
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix QuadMesh.set_norm to avoid redundant norm callbacks |
| `I2` | Instructions | Problem description |
| `I3` | Instructions | Key idea |
| `R1` | Rules | Nothing is established about this subject yet |





## Instructions

### I1 — Fix QuadMesh.set_norm to avoid redundant norm callbacks

Remove the colorbar update in the `set_norm` method to prevent multiple norm callbacks. The method should simply call the superclass implementation:
```python
    def set_norm(self, norm):
        """Set a new norm without triggering redundant colorbar updates."""
        super().set_norm(norm)
```

### I2 — Problem description

Setting the norm of a QuadMesh after a colorbar has been created fails in Matplotlib 3.6.3, raising `ValueError: Invalid vmin or vmax` during rendering.

### I3 — Key idea

`QuadMesh.set_norm` must also update the attached colorbar’s normalization and color limits, and ensure callbacks are registered only once.

## Rules

### R1 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `matplotlib__matplotlib-25079`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

## References

- `skill_load(name="matplotlib-matplotlib-25079", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

