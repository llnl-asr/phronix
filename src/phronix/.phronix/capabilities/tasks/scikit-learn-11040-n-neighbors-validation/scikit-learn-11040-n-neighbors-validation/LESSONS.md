# Lessons — scikit-learn-11040-n-neighbors-validation

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Incorrect exception type for non‑integer n_neighbors

The test expects a TypeError when n_neighbors is a float, but the code raises ValueError. Adjust validation to raise TypeError for non‑integer values.

## Lessons
