# Lessons — scikit-learn-scikit-learn-25570

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Returning early may hide other bugs

If future changes introduce additional empty‑feature scenarios, this guard may mask them; ensure tests cover all expected transformer configurations.

### P2 — Incorrect placement of guard

Placing the guard before `feature_names_outs` is defined will cause a NameError. It must follow the construction of `feature_names_outs`.

## Lessons
