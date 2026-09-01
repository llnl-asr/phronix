# Lessons — psf-requests-3362

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Assuming iter_content works like iter_lines

Leads to type errors and incorrect handling of partial Unicode characters.

### P2 — Changing unrelated code

Spends time and may cause regressions; focus solely on the iter_content usage.

## Lessons
