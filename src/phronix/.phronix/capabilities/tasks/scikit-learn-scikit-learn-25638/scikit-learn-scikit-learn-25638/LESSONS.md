# Lessons — scikit-learn-scikit-learn-25638

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Conversion alone insufficient

Converting pandas Series to NumPy arrays inside unique_labels stops the immediate 'unknown' error but downstream validation still fails because dtype checks occur earlier; full support requires updating validation helpers as well.

### P2 — Incorrect dtype mapping

Mapping nullable dtypes to object dtype reintroduces 'unknown' type errors; ensure they are mapped to proper integer, float, or bool dtypes.

## Lessons
