# Lessons — scikit-learn-scikit-learn-15535

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — mutual_info_score regression not fixed by .astype removal

Removing .astype(object) from input does not resolve the regression in mutual_info_score input validation; the ValueError persists indicating deeper issue in scikit-learn 0.24.1

## Lessons
