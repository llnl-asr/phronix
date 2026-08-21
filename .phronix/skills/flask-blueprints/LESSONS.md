# Lessons — flask-blueprints

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Assert check did not satisfy test expectations

**2026-08-21** — The added `assert "." not in name` caused an AssertionError, but the tests expect a ValueError when a dotted blueprint name is used. Asserts may be stripped in optimized mode and are not the right exception type. Replace the assert with an explicit check that raises ValueError with a clear message.

Why: The test `test_dotted_name_not_allowed` still failed, showing the validation was not exercised as needed. The fix requires proper exception handling rather than an assert.
