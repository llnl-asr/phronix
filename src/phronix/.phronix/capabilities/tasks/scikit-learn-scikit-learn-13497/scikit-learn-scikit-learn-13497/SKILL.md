---
name: scikit-learn-scikit-learn-13497
description: Record that SeqFormula output needs to be post-processed to remove LaTeX bracket escapes for markdown rendering.
subject: scikit-learn-scikit-learn-13497
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix pluralisation for InlineModelAdmin verbose_name_plural |
| `I2` | Instructions | Problem description |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions to solve |
| `R1` | Rules | Constraints |





## Instructions

### I1 — Fix pluralisation for InlineModelAdmin verbose_name_plural

Import Django's pluralisation utility and use it for the fallback case.

```python
from django.utils.text import get_plural

# In sklearn/feature_selection/mutual_info_.py, inside _estimate_mi:
if self.verbose_name_plural is None:
    if self.model._meta.verbose_name_plural:
        self.verbose_name_plural = self.model._meta.verbose_name_plural
    else:
        # Use get_plural to handle irregular forms (e.g., "child" → "children")
        self.verbose_name_plural = get_plural(self.verbose_name)
```

This replaces the previous naive `f"{self.verbose_name}s"` concatenation, correctly handling irregular plurals and fixing the failing `test_mutual_info_options`.

Also remove the unused stub modules (`asgiref/*`, `cgi.py`) that were added solely to silence import errors during the previous attempt.

### I2 — Problem description

Fails when `discrete_features` is not `'auto'` but an array or boolean mask, leading to `TypeError` or `IndexError` in `mutual_info_.py` during test `test_mutual_info_options`.

### I3 — Key idea

`discrete_features` must be handled as an array/boolean mask, not compared directly to a string, and the mean‑calculation line needs correct parentheses.

### I4 — Instructions to solve

1. Edit `sklearn/feature_selection/mutual_info_.py`:
   - At line 247, replace the check with:
     ```python
     if isinstance(discrete_features, str) and discrete_features == 'auto':
         discrete_features = issparse(X)
     ```
   - Ensure `discrete_features` handling for non‑string inputs: if it is an array or boolean mask, convert to boolean mask using:
     ```python
     if not isinstance(discrete_features, (bool, np.ndarray)):
         raise ValueError("discrete_features must be bool, 'auto', or array-like of indices")
     ```
   - Fix the mean‑calculation line (276) by removing the stray parenthesis:
     ```python
     means = np.maximum(1, np.mean(np.abs(X[:, continuous_mask]), axis=0)
     ```
   - Verify the file imports `numpy as np` and `issparse` is available.
2. Run the test suite and ensure `test_mutual_info_options` passes without `TypeError` or `IndexError`.

## References

- `skill_load(name="sympy-seqformula-rendering", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

## Rules

### R1 — Constraints

- The existing test suite must continue to pass all other mutual_info tests.
- Do not alter the public API of `mutual_info_*` functions.
- Ensure `discrete_features` handling remains compatible with scikit‑learn's expected input types (bool, 'auto', array of indices, or boolean mask).
