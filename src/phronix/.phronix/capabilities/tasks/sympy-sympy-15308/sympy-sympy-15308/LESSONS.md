# Lessons — sympy-sympy-15308

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — After applying the fallback compile handling and LaTeX Trace fix, test

**2026-08-29** — After applying the fallback compile handling and LaTeX Trace fix, tests still failed:
- test_latex_symbols_failing: expected symbolic equality LaTeX but got '\mathrm{False}'.
- test_builtin_without_args_mismatched_names: expected '\mathcal{COS}' but got '\operatorname{CosineTransform}'.
- test_issue_8470: expected 'A \left(- B\right)' but got '- A B'.
- test_issue_13559: expected '\frac{5}{1}' but got '5'.
- test_trace: expected '\mathrm{tr}\left (A \right )' but got 'Trace(A)'.
- test_print_basic: expected '\mbox{Tr}\left(%s\right)' formatting for UnimplementedExpr but got plain form.
These failures indicate further fixes needed in LaTeX printer handling of symbols, builtins, sign handling, rational formatting, and generic fallback for unimplemented expressions.
