# Lessons — sympy-sympy-12236

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Only fixing imports does not resolve failing target tests

The failing `test_div` and related algebraic tests stem from deeper bugs, not import issues. Applying only these patches will not make the target test pass.

### P2 — Running full test suite slows feedback

Re‑running the entire SymPy test suite after each small edit wastes time. Isolate failing target tests (`test_div`) to get quicker feedback.

## Lessons
