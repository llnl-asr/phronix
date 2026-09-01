# Lessons — sympy-dmp-zz-mignotte-bound

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Knuth-Cohen bound replacement failed - no patch generated

Attempt to replace mignotte bound with knuth-cohen bound produced no code changes; the approach was insufficient because the existing function signatures and expected behavior were not correctly handled, leading to no applicable patch.

## Lessons
