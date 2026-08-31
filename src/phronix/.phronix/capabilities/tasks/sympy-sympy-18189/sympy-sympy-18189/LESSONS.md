# Lessons — sympy-sympy-18189

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Permute order-dependence pitfall

**2026-08-29** — Pitfall: permute=True produces different results based on symbol order. Root cause: permute paths (do_permute_signs, permute_few_signs, do_permute_signs_var) are conditional on equation type from classify_diop(), which sorts variables via default_sort_key. Fix: Replace conditional elif chain with uniform `elif permute: final_soln.update(set(signed_permutations(sol)))` ensuring permute=True always applies signed_permutations regardless of equation classification path. Lesson: Always test diophantine solver with both symbol orderings when permute=True is used.
