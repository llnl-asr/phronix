# Lessons — sympy-sympy-24152

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfalls and lessons

**2026-08-29** — Pitfall: Using `isinstance(tp, TensorProduct)` to decide whether to recursively expand fails when scalar factors are present, because `TensorProduct.__new__` returns a `Mul` object containing both the scalar part and the `TensorProduct` — not a plain `TensorProduct`. This causes the expansion to be incomplete, missing terms like the second tensor factor.

Lesson: Always use `args_cnc()` to properly separate commutative (scalar) factors from the non-commutative part before checking for a `TensorProduct`. The `args_cnc()` method correctly handles both cases:
- When `tp` is a plain `TensorProduct` (no scalar factors): `c_part` is empty, `nc_part` contains the `TensorProduct`
- When `tp` is a `Mul` with scalar factors (e.g., `2*Ux(U + V)`): `c_part` contains the scalars, `nc_part` contains the `TensorProduct`

The original `isinstance` check only works for case (a), missing all expansions involving scalar factors. The `args_cnc()`-based fix handles both cases and enables complete expansion in a single call.
