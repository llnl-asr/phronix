# Lessons — sympy-sympy-15609

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Attempt 3 failed to fix the double‑subscript bug in the LaTeX printer

**2026-08-29** — Attempt 3 failed to fix the double‑subscript bug in the LaTeX printer. The patch changed `_print_Indexed` to strip leading underscores, but the `test_MatrixElement_printing` still produced `M_{i, _i_1}` instead of `M_{i, i_{1}}`. The failure indicates that the leading underscore originates earlier, in `_print_IndexedBase`, which still adds braces around the label and does not handle existing underscores, causing a double subscript. The test suite also showed other LaTeX related failures unrelated to this change.

### L2 — Pitfall: Underscore stripping insufficient

**2026-08-29** — Only stripping leading underscores does not handle cases where the underscore is not leading; the double subscript can still appear. Future fixes must consider the full LaTeX generation logic, not just a simple strip.
