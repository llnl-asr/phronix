# Lessons — scikit-learn-scikit-learn-25747

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pitfall: Only converting Series may miss other output types

Simply converting Series to DataFrames does not handle cases where transformers return numpy arrays or other structures, which can still cause mismatches. Ensure all outputs are uniformly DataFrames before concatenation.

## Lessons
