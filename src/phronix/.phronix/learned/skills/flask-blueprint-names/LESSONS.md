# Lessons — flask-blueprint-names

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Disallow dots in blueprint names

**2026-08-21** — Symptom: tests `test_dotted_name_not_allowed` and `test_route_decorator_custom_endpoint_with_dots` fail because Flask permits blueprint names with a dot. Root cause: Blueprint constructor lacks validation for prohibited characters, unlike endpoint name validation. Fix: add a check in the Blueprint constructor to raise a `ValueError` when the name contains a dot. This mirrors existing endpoint name validation and satisfies the tests.
