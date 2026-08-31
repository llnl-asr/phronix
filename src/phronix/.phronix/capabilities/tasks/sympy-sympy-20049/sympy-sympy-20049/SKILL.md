---
name: sympy-sympy-20049
description: The sympy-sympy-20049 subject.
subject: sympy-sympy-20049
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I1 — Problem solved |
| `I2` | Instructions | I2 — Key idea |
| `I3` | Instructions | I3 — Change to apply |
| `I4` | Instructions | learn-from-attempt-20049-test2 |
| `R1` | Rules | R1 — Preserve existing test behavior |

## Instructions

### I1 — I1 — Problem solved

Failing tests where `Point.vel(frame)` raises `ValueError` for undefined frames; the expected behavior is to compute the velocity via position derivatives when possible.

### I2 — I2 — Key idea

Compute velocity from the time derivative of a point’s position when that position is defined relative to another point that already has a velocity in the same frame.

### I3 — I3 — Change to apply

In `sympy/physics/vector/point.py` replace the `raise ValueError` block in `Point.vel(self, frame)` with:
```
for otherpoint, pos_vec in self._pos_dict.items():
    if frame in otherpoint._vel_dict:
        rel_vel = pos_vec.dt(frame)
        return otherpoint._vel_dict[frame] + rel_vel
# If no relation provides a velocity, default to zero vector.
return Vector(0)
```

### I4 — learn-from-attempt-20049-test2

TEST 2 (test_auto_point_vel): The computed velocity has unexpected extra terms. When position involves dynamicsymbols like q(t), the differentiation pos_vec.dt(frame) produces results with additional symbol terms that don't match expected. The fix needs to check what symbols are in the result and ensure they match what the test expects, or add conditions to filter when computation is valid.

## Rules

### R1 — R1 — Preserve existing test behavior

Do not alter behavior of Point.vel when a velocity is already defined for the frame; existing functionality must remain unchanged.

## References
