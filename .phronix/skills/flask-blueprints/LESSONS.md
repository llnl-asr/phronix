# Lessons — flask-blueprints

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Blueprint names may contain dots

**2026-08-21** — The test `test_route_decorator_custom_endpoint_with_dots` expects blueprint names with dot characters to be accepted. Raising a ValueError for dot in the name caused the test to fail. Blueprint names should be allowed to contain dots, or the test expectations must be updated accordingly. Remove the dot‑check to fix the failure.
