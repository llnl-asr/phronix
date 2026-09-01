# Lessons — django-django-14752

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfalls and lessons

**2026-08-29** — - Attempting to directly override `AutocompleteJsonView.get` leads to duplicated logic and maintenance burden; future changes to `get` require updating every subclass.
- Adding custom fields without a helper method caused test failures because the original result dict was hard‑coded.
- Forgetting to include permission checks in the refactored method broke security; ensure `has_perm` is called before constructing results.
- Placing `serialize_result` after other helper methods caused a NameError in older Django versions; define it before it is referenced.
- Not updating the docstring of `get` resulted in outdated documentation, confusing future developers.
