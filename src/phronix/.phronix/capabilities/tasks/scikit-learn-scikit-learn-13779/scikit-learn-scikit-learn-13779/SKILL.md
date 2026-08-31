---
name: scikit-learn-scikit-learn-13779
description: The scikit-learn-scikit-learn-13779 subject.
subject: scikit-learn-scikit-learn-13779
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update fitting loop to skip None estimators |
| `I2` | Instructions | Map fitted estimators back to original order |
| `I3` | Instructions | one-line fix for None estimator with sample_weight in VotingClassifier |
| `I4` | Instructions | how to verify the fix works |
| `R1` | Rules | Do not alter estimator order or names |
| `R2` | Rules | Preserve existing regression test behavior |
| `R3` | Rules | do not delete __check_build module for this bug |
| `R4` | Rules | do not add None guard in _parallel_fit_estimator |

## Instructions

### I1 — Update fitting loop to skip None estimators

Replace the existing Parallel fitting block with a new block that fits only non-None estimators, stores results, and aligns them with estimator names, preserving None entries.

### I2 — Map fitted estimators back to original order

After fitting, iterate over original (name, estimator) pairs; if estimator is None, keep None, else assign the next fitted estimator from the results, updating self.estimators_ and self.named_estimators_ accordingly.

### I3 — one-line fix for None estimator with sample_weight in VotingClassifier

When set_params() sets an estimator to None and fit() is called with sample_weight, the _parallel_fit_estimator function in sklearn/ensemble/voting.py receives None as the estimator and calls .fit() on it, causing AttributeError: 'NoneType' object has no attribute 'fit'.

The fix: At sklearn/ensemble/voting.py line 81, add step is not None and guard before the has_fit_parameter() call. Change the validation loop condition to check for None before calling has_fit_parameter. This prevents the AttributeError when None estimators are encountered in the validation loop.

### I4 — how to verify the fix works

Run the two target tests to confirm they pass: sklearn/ensemble/tests/test_voting.py::test_none_estimator_with_weights[X0-y0-voter0] and sklearn/ensemble/tests/test_voting.py::test_none_estimator_with_weights[X1-y1-voter1]. Also verify 18 regression tests continue to pass.

## Rules

### R1 — Do not alter estimator order or names

The order and naming of estimators must remain identical to the input list, including None placeholders.

### R2 — Preserve existing regression test behavior

All existing tests that previously passed must still pass after the change.

### R3 — do not delete __check_build module for this bug

Deleting the __check_build module is a red herring unrelated to the voting bug. The error occurs in the has_fit_parameter() validation loop, not in __check_build. This cleanup was tried in attempt-1 and failed — 0 of 2 target tests passed.

### R4 — do not add None guard in _parallel_fit_estimator

Do NOT add if estimator is None: return None in _parallel_fit_estimator. The error occurs before that function is reached; the failure is in the has_fit_parameter() validation loop at lines 79-83. Adding a guard there only masks the real issue.

## References

- `skill_load(name="scikit-learn-scikit-learn-13779", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
