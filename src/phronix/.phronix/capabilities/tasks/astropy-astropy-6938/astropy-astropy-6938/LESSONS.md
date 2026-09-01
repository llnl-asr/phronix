# Lessons — astropy-astropy-6938

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — In-place replace does not modify output_field

The original attempt failed because `replace` returned a new array without assigning it back, leaving the exponent unchanged.

### P2 — Incorrect test expectations

Updating the code without adjusting test expectations will cause checksum mismatches.

## Lessons
