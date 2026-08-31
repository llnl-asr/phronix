# Lessons — django-django-14155

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Incorrect ordering/quoting of partial args

Attempted to include partial arguments directly in __repr__ but the ordering and quoting did not match Django's expectations, causing test failures.

### P2 — Unhandled nested partials

Nested functools.partial objects were not considered, so representations for nested partials remain incorrect.

## Lessons

### L1 — Failed representation of ResolverMatch when func is functools

**2026-08-29** — Failed representation of ResolverMatch when func is functools.partial. Expected string includes the partial object itself, but previous implementation unwrapped it and showed func_path with partial args separately, causing test failures in test_repr_functools_partial and test_repr_functools_partial_nested.
