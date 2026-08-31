# Lessons — flask-blueprint-validation

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — dot validation interferes with endpoint dot handling

**2026-08-26** — Adding dot validation to Blueprint name interferes with endpoint dot handling tests. The validation raised ValueError for any blueprint name containing a dot, which caused test_route_decorator_custom_endpoint_with_dots to fail because the test expects errors related to endpoint parsing, not blueprint name validation. The check was added to `Blueprint.__init__` but did not fire for the path the test uses.
