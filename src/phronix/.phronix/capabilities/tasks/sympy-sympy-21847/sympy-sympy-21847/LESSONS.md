# Lessons — sympy-sympy-21847

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pitfall: Using `max(powers

Pitfall: Using `max(powers.values())` for min_degrees filtering checks max single-variable exponent, not total degree. The fix is `sum(powers.values())` to match docstring: "min_degree <= total_degree(monom) <= max_degree". This loss of mixed monomials like x*x**2 when min_degrees equals max_degrees was the bug.

## Lessons
