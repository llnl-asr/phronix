# Lessons — sympy-sympy-13971

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pre-existing test failures

Do not revert the fix because of these pre-existing failures: test_latex_symbols_failing, test_builtin_without_args_mismatched_names, test_issue_8470, test_issue_13559. These failures exist independently of the SeqFormula bracket fix and were present before any changes were made.

## Lessons
