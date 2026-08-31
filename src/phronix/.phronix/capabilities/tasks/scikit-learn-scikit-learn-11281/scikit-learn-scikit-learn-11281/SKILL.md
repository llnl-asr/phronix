---
name: scikit-learn-scikit-learn-11281
description: The django-numberformat-empty-string-fix subject.
subject: scikit-learn-scikit-learn-11281
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add fit_predict method |
| `I2` | Instructions | Store training labels in fit |
| `I3` | Instructions | apply-fix-to-numberformat |
| `R1` | Rules | Preserve existing API behavior |
| `R2` | Rules | Maintain regression test pass |

## Instructions

### I1 — Add fit_predict method

In `sklearn/mixture/base.py` implement a `fit_predict(self, X, y=None)` that calls `self.fit(X, y)` and returns `self.labels_`.

### I2 — Store training labels in fit

Modify the `fit` method to set `self.labels_ = self.predict(X)` after fitting the model.

### I3 — apply-fix-to-numberformat

Add two guard clauses at the start of the format() function body after the docstring in django/utils/numberformat.py to handle None and empty string inputs:
if number is None:
    return ""
if number == "":
    return ""

## Rules

### R1 — Preserve existing API behavior

Do not alter the signature or semantics of existing methods other than adding `self.labels_`.

### R2 — Maintain regression test pass

All existing regression tests (43) must continue to pass.

## References
