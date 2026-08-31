---
name: scikit-learn-scikit-learn-12471
description: Fix handling of unknown string categories in OneHotEncoder when handle_unknown='ignore'.
subject: scikit-learn-scikit-learn-12471
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Fix steps |
| `R1` | Rules | Maintain existing test suite |
| `R2` | Rules | Do not alter handling of numeric categories |

## Instructions

### I1 — Problem description

OneHotEncoder raises ValueError for unknown string categories when handle_unknown='ignore' because it attempts to fill unknown entries with the first known category, causing truncation errors.

### I2 — Key idea

Zeroing out entries for unknown categories is insufficient; the underlying issue is that unknown strings are still processed by _encode, leading to ValueError before the zero‑out can apply.

### I3 — Fix steps

1. In sklearn/preprocessing/_encoders.py, inside _transform, after computing valid_mask, add a guard to skip encoding for unknown categories before calling _encode.
2. Replace the block that sets X_int[~valid_mask, i] = 0 with a conditional that only applies when no unknown string remains after mask.
3. Ensure the function returns X_int and X_mask without invoking _encode on unknown entries.

## Rules

### R1 — Maintain existing test suite

All existing regression tests (53) must continue to pass.

### R2 — Do not alter handling of numeric categories

The fix must only affect string categories; numeric handling should remain unchanged.
