# Lessons — sympy-24152

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfall: Incomplete handling of Mul without TensorProduct

**2026-08-29** — Attempted to simply split scalar factors using `c_part, nc_part = tp.args_cnc()` but missed cases where `nc_part` had no TensorProduct, leading to loss of terms. Must check for presence of TensorProduct before recursive expansion.
