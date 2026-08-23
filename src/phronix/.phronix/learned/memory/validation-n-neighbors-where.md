---
name: validation-n-neighbors-where
description: Place n_neighbors validation in the fit method rather than __init__ to avoid premature ValueError in tests
metadata:
  type: lesson
---

**Why:** The test suite expects `NeighborsBase` to accept a float `n_neighbors` at construction and raise a `ValueError` only during fitting or usage. Adding validation in `__init__` causes immediate exception, breaking tests like `test_n_neighbors_datatype`.

**How to apply:** Move the integer and positivity checks for `n_neighbors` from `NeighborsBase.__init__` to the `fit` method (or a validation helper called during fitting). Raise `ValueError` with clear messages when invalid.

**Lesson:** Validation that impacts API usage should occur at the appropriate lifecycle stage to align with test expectations and user experience.
