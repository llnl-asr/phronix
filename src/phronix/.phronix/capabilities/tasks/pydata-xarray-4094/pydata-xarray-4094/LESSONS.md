# Lessons — pydata-xarray-4094

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Over‑catching exceptions

Wrapping the whole `to_unstacked_dataset` method in a broad `try/except` caused genuine bugs to be hidden and made debugging harder. Scope the exception handling to the selection of each level only.

## Lessons
