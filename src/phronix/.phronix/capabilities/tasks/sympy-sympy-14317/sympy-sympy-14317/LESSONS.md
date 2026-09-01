# Lessons — sympy-sympy-14317

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Setting the default order to "lex" in LatexPrinter did not fix all LaT

**2026-08-29** — Setting the default order to "lex" in LatexPrinter did not fix all LaTeX printing tests. Specifically, test_latex_Poly_order still failed, and other unrelated tests (symbols, builtin_without_args_mismatched_names, issue_8470, issue_13559) also failed, indicating the change was insufficient and introduced regressions.
