# Lessons — sympy-sympy-11400

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pitfall: Double-application bug with sin(x)/x mapping

Adding "sinc": "sin(x)/x" to known_functions causes ccode(sinc(x)) to output "sin(x)/x(x)" — the expression sin(x)/x gets wrapped with (x) appended, suggesting the printer applies the printed string as a function call to x. This was the main failure mode in the first attempt. The fix must ensure the output is just "sin(x)/x" without double-application. The root cause is in how CodePrinter._print_Function() processes the mapped string — it may be treating the argument x as a function call. This pitfall documents why a simple string mapping needs careful verification.

## Lessons

### L1 — Lesson: sinc mapping requires output verification

**2026-08-29** — When adding "sinc": "sin(x)/x" to known_functions, verify the actual ccode(sinc(x)) output produces "sin(x)/x" without the double-application bug (sin(x)/x(x)). The first attempt added the mapping but the test still failed because the printer's _print_Function() method apparently wrapped the output with (x). A later run must test the actual output after making the change, not assume the mapping alone is sufficient.
