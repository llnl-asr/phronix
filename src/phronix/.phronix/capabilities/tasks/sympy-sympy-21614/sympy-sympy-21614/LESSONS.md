# Lessons — sympy-sympy-21614

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Server error prevented fix for Derivative.kind

**2026-08-29** — Attempt to fix Derivative.kind returning UndefinedKind failed due to server-side API error (500 Internal Server Error - model output does not match expected peg-native format). No code changes were made. The issue involves Derivative.kind returning UndefinedKind for matrix-valued expressions when it should return the correct kind (e.g., MatrixKind). Next attempt should avoid server errors by using a different model or approach, and should focus on the Derivative.kind attribute implementation in sympy.
