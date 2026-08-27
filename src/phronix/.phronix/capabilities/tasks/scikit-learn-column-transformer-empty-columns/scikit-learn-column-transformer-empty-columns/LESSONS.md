# Lessons — scikit-learn-column-transformer-empty-columns

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Reordering empty-column check breaks fitted_transformers assertion

**2026-08-26** — **Symptom:** AssertionError at sklearn/compose/_column_transformer.py:606 (`assert not list(fitted_transformers)`) when attempting to reorder the _is_empty_column_selection check before the passthrough check in _update_fitted_transformers.

**Why it failed:** The assertion validates that the fitted_transformers iterator is completely consumed during the loop. When empty-column transformers skip consumption (because they don't need a fitted transformer), leftover items remain in the iterator, causing the assertion to fail.

**What was tried:** Moving `elif _is_empty_column_selection(column):` BEFORE `elif old == "passthrough":` in _update_fitted_transformers to prevent empty transformers from consuming a fitted transformer.

**The root issue:** The fix only addresses consumption in _update_fitted_transformers but doesn't handle how fitted_transformers is built. Either fitted_transformers should exclude empty-column transformers from the start, or the handling must be different. The assertion is a safety check that catches incomplete solutions.
