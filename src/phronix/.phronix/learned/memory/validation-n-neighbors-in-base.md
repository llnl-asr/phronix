---
name: validation-n-neighbors-in-base
description: Added integer and positivity validation for n_neighbors in NeighborsBase __init__
metadata:
  type: lesson
---

**Why:** The Neighbors estimators should reject non-integer or non-positive n_neighbors to provide clearer errors and avoid TypeError later.

**How to apply:** Include a type and range check for `n_neighbors` in `NeighborsBase.__init__` before assigning it. Raise `ValueError` with informative messages if invalid.

**Lesson:** Adding validation prevents downstream errors when users inadvertently pass floats, improving API robustness.
