# Lessons — scikit-learn-scikit-learn-14894

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — No fix produced - agent missed the issue

**2026-08-29** — Attempt produced no diff - agent did not understand the issue of ZeroDivisionError in _sparse_fit when support_vectors_ is empty. The root cause is division by zero at dual_coef_indices.size / n_class when n_class could be 0 with empty support vectors. Expected fix: handle empty support_vectors_ case, producing self.dual_coef_ = sp.csr_matrix([]).
