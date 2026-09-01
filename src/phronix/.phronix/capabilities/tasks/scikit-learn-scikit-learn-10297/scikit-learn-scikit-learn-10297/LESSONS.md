# Lessons — scikit-learn-scikit-learn-10297

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfalls and lessons

**2026-08-29** — - Previous attempts that failed likely tried to add the parameter without passing it to the parent, or added it to the wrong method
- The fix is minimal - just declaration and pass-through; the actual CV logic already exists in parent classes
- This pattern (parameter passing through to parent) is already used by RidgeCV class, so following it ensures consistency
- Don't modify test files - the test test_ridge_classifier_cv_store_cv_values was already written to verify this fix
- The infrastructure already existed - _BaseRidgeCV already accepts store_cv_values and _RidgeGCV already handles it for CV
- A wrong corrector left in place misleads every future attempt on this subject
- The difference between healing something and complaining about it: a corrector must be deterministic and verifiable
