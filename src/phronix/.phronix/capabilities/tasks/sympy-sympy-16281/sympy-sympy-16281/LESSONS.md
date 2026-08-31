# Lessons — sympy-sympy-16281

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfalls and lessons

**2026-08-29** — - Attempted to modify the pretty printer without adding a regression test, causing the harness to report "agent produced no patch" because no concrete change was made.
- Changing only the visual spacing without adjusting width calculations broke existing tests for other expressions.
- Removing the trailing newline alone was insufficient; the underlying bar‑width logic also needed adjustment to avoid asymmetric output.
- Skipping the addition of a targeted test for the `Product` rendering resulted in the fix not being verified, leading to the task being marked unresolved.
