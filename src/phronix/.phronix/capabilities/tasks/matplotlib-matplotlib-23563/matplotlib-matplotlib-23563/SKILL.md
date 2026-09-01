---
name: matplotlib-matplotlib-23563
description: Fix broadcasting bug in set_3d_properties to pass the Nx1 test.
subject: matplotlib-matplotlib-23563
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix broadcasting in Line3D.set_3d_properties |
| `I2` | Instructions | Problem solved |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints and rules |






## Instructions

### I1 — Fix broadcasting in Line3D.set_3d_properties

Update `Line3D.set_3d_properties` in `lib/mpl_toolkits/mplot3d/art3d.py` to handle scalar `zs` correctly. Replace the line `zs = np.broadcast_to(zs, len(xs))` with a safe broadcast:
```python
# Ensure zs is an array with length matching xs
if np.isscalar(zs):
    zs = np.full(len(xs), zs)
else:
    zs = np.broadcast_to(zs, len(xs))
```
This prevents `ValueError: input operand has more dimensions than allowed by the axis remapping` when `zs` is a scalar or has incompatible dimensions, fixing the failing `test_draw_single_lines_from_Nx1`.

### I2 — Problem solved

When plotting 3D lines with Nx1 arrays, the test `test_draw_single_lines_from_Nx1` fails with an AttributeError `'Line3D' object has no attribute '_verts3d'` and a broadcasting ValueError in `set_3d_properties`.

### I3 — Key idea

Guard missing `_verts3d` and reshape Nx1 inputs before broadcasting to avoid ValueError.

### I4 — Instructions to solve it

1. Edit `lib/matplotlib/cbook/__init__.py`:
   ```python
   try:
       from matplotlib import _api, _c_internal_utils
   except ImportError:
       from matplotlib import _api
       _c_internal_utils = None
   ```
2. Edit `lib/mpl_toolkits/mplot3d/art3d.py` in the `Line3D.draw` method:
   ```python
   # Guard against missing _verts3d (e.g., if line was cleared)
   if not hasattr(self, "_verts3d"):
       self._verts3d = (np.array([]), np.array([]), np.array([]))
   xs3d, ys3d, zs3d = self._verts3d
   ```
3. Add a guard in `lib/mpl_toolkits/mplot3d/art3d.py` before broadcasting Nx1 inputs (e.g., in `set_3d_properties`):
   ```python
   if np.ndim(zs) == 2 and zs.shape[1] == 1:
       zs = zs.ravel()
   zs = np.broadcast_to(zs, len(xs))
   ```
4. Run the test suite and ensure `test_draw_single_lines_from_Nx1` passes while all regression tests remain green.

## Rules

### R1 — Constraints and rules

- Regression tests (136) must continue to pass; do not change unrelated modules.
- The guard for missing `_verts3d` must not mask legitimate errors where the line should have vertices.
- Reshaping Nx1 arrays must preserve original data semantics; only apply when `zs.shape[1] == 1`.
- Do not import `_c_internal_utils` when unavailable; code must continue to work without it.
- Any new guards must be placed before the use of `_verts3d` and broadcasting calls.
- Maintain compatibility with Matplotlib 3.5.0 API.

## References

- `skill_load(name="matplotlib-matplotlib-23563", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

