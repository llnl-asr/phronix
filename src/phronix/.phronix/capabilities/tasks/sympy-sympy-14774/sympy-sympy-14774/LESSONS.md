# Lessons — sympy-sympy-14774

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfalls and lessons

**2026-08-29** — - Pitfall: Initially the `inv_trig_table` only contained `["asin", "acos", "atan", "acot"]`, so `acsc` and `asec` were not recognized as inverse trig functions and would not get proper LaTeX formatting (abbreviated "acsc"/"asec", full "arccsc"/"arcsec", or power "csc^-1"/"sec^-1" styles). This is the exact problem the fix addresses.
- Pitfall: The test run showed 4 failures in unrelated tests (`test_latex_symbols_failing`, `test_builtin_without_args_mismatched_names`, `test_issue_8470`, `test_issue_13559`), but these were pre-existing failures caused by `'False'` constant issues, not related to the `inv_trig_table` change. These should not be mistakenly attributed to the fix.
- Lesson: The fix follows the exact pattern established by other SymPy printing modules (octave.py, julia.py) which already include all six inverse trig functions. Always check existing patterns before making changes.
- Lesson: The change is minimal (2 characters added to a list) but has significant impact — it enables proper LaTeX printing of `acsc` and `asec` functions that were previously falling back to `\\operatorname{acsc}` / `\\operatorname{asec}` instead of the full `\\operatorname{arccsc}` / `\\operatorname{arcsec}` style.
- The original task was resolved: 1 of 1 target test passed and all 114 regression tests passed after the fix.
