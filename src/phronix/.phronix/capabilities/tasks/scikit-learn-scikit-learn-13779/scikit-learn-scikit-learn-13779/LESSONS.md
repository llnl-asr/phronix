# Lessons — scikit-learn-scikit-learn-13779

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — do not delete __check_build module for voting None estimator bug

Deleting __check_build module was a red herring — unrelated to the voting bug. Attempt-1 tried this and got 0 of 2 target tests passing. The error occurs in the has_fit_parameter() validation loop, not in __check_build.

### P2 — do not add None guard in _parallel_fit_estimator for voting bug

Adding if estimator is None: return None in _parallel_fit_estimator does not fix the issue. The error occurs before that function is reached; the failure is in the has_fit_parameter() validation loop. This was tried in attempt-1 and failed.

## Lessons
