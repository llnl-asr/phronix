# Lessons — sympy-15609-latex-printer

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Double subscript '_' in LaTeX output

Indexed matrix-expression LaTeX printer produces a double subscript '_' which breaks MathJax rendering. No patch was generated; need to fix LaTeX generation to avoid double underscores.

## Lessons
