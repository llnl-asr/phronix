---
name: scikit-learn-scikit-learn-10508
description: The scikit-learn-scikit-learn-10508 subject.
subject: scikit-learn-scikit-learn-10508
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add guard for empty input in transform |
| `I2` | Instructions | LabelEncoder transform empty list failure with string classes |
| `I3` | Instructions | Fix LabelEncoder.transform([]) for empty lists with string labels |
| `R1` | Rules | Preserve existing behavior for non‑empty inputs |
| `R2` | Rules | Error messages must match test expectations |

## Instructions

### I1 — Add guard for empty input in transform

In `sklearn/preprocessing/label.py` within `LabelEncoder.transform`, after converting `y` to a 1‑d array, insert:
```python
if y.size == 0:
    return np.array([], dtype=int)
```

### I2 — LabelEncoder transform empty list failure with string classes



### I3 — Fix LabelEncoder.transform([]) for empty lists with string labels

I7 - Fix LabelEncoder.transform([]) TypeError when fitted on string labels. column_or_1d([]) returns float64 array but self.classes_ has unicode dtype, causing np.searchsorted to fail with TypeError: Cannot cast array data from dtype('float64') to dtype('<U32').

I9 - Skill contains: problem description, fix instructions, constraints, pitfalls. Does NOT contain verified outcomes or test results.

Problem: LabelEncoder.transform([]) raises TypeError when encoder was fitted on string labels because column_or_1d([]) creates float64 array incompatible with string self.classes_ dtype in np.searchsorted.

Instructions: In sklearn/preprocessing/label.py transform method, add after `y = column_or_1d(y, warn=True)`:
  if len(y) == 0:
      return np.array([], dtype=np.intp)
This guard must be placed BEFORE `classes = np.unique(y)` and BEFORE `np.searchsorted(self.classes_, y)`.

Constraints: 
- Must NOT modify inverse_transform
- Must NOT change error message format for test_label_encoder_errors  
- Must keep all 18 regression tests passing
- Fix must not affect non-empty input code paths
- Guard after column_or_1d, before any other processing

Pitfalls to avoid:
- Do NOT use wrong dtype (np.intp is correct for integer index output)
- Do NOT broaden fix beyond empty-y guard
- Earlier attempt failing on error message format was due to placement/or timing, not the dtype itself

## Rules

### R1 — Preserve existing behavior for non‑empty inputs

All existing logic for transforming and inverse transforming non‑empty inputs must remain unchanged.

### R2 — Error messages must match test expectations

For empty input, `inverse_transform` should raise `ValueError` with message `'bad input shape ()'` as expected by the test.

## References
