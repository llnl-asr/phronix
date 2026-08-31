# Lessons — sympy-sympy-13895

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — real_root misuse leads to complex results

**2026-08-29** — Unconditional use of `real_root` in `_denest_pow` caused complex results, breaking tests `test_powers_Integer` and `test_issue_13890`.
