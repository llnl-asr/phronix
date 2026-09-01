# Lessons — matplotlib-matplotlib-25332

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — AttributeError during draw

Removing `_align_label_groups` without guarding its access causes `AttributeError` in `axis._update_label_position`.

### P2 — Introduced regressions

Previous attempts caused failures in `test_pickle.py::test_polar`.

## Lessons
