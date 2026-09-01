# Lessons — matplotlib-pickle-alignment

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Missing _align_label_groups after state cleanup

**2026-08-27** — Removing alignment groups from Figure state causes AttributeError when other parts of code expect _align_label_groups attribute during drawing, leading to failures in test_complete and test_polar.
