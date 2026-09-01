# Lessons — django-django-12184

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfalls and Lessons

**2026-08-31** — * Adding a default argument to the view signature solves the TypeError, but forgetting to adjust any internal logic that assumes `format` is always provided can cause subtle bugs later.
* If other view functions reuse the same URL pattern name, ensure they also handle missing parameters consistently.
* Testing only the failing test may miss regression in other views that rely on the same optional group; run the full test suite after the change.
* Modifying the URL regex without understanding the optional group semantics can introduce double slashes or empty string captures; keep the existing pattern unchanged unless necessary.
