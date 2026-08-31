---
name: sympy-sympy-24102
description: fix parse_mathematica fallback
subject: sympy-sympy-24102
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem |
| `I2` | Instructions | Diagnosis |
| `I3` | Instructions | Key Idea |
| `I4` | Instructions | Instructions |
| `I5` | Instructions | Fix parse_mathematica fallback |
| `R1` | Rules | Constraint |

## Instructions

### I1 — Problem

The `parse_mathematica` function in SymPy 1.11 fails to parse bare Greek characters such as λ (lambda). Attempting `parse_mathematica('λ')` raises a `SympifyError` caused by a `SyntaxError`. This regression broke existing code that relied on the previous `mathematica` parser which handled Greek letters correctly.

### I2 — Diagnosis

The previous attempt attempted to create a skill for sympy-24102 but did not record a diagnosis. The task was to write a diagnosis based on the contents of research-2.md, which was not found. As a result, the diagnosis is missing and future attempts will lack guidance.

### I3 — Key Idea

`parse_mathematica` lacks a translation rule for bare Greek letters; adding a mapping for these characters resolves the parsing error.

### I4 — Instructions

1. Open `sympy/parsing/mathematica.py`.
2. Locate the dictionary that maps Mathematica symbols to SymPy symbols (e.g., `MATHEMATICA_SYMBOLS`).
3. Add entries for the Greek letters that need to be supported, e.g.:
   ```python
   MATHEMATICA_SYMBOLS.update({
       "α": Symbol('alpha'),
       "β": Symbol('beta'),
       "γ": Symbol('gamma'),
       "δ": Symbol('delta'),
       "ε": Symbol('epsilon'),
       "ζ": Symbol('zeta'),
       "η": Symbol('eta'),
       "θ": Symbol('theta'),
       "ι": Symbol('iota'),
       "κ": Symbol('kappa'),
       "λ": Symbol('lambda'),
       # add other needed Greek letters here
   })
   ```
4. Ensure the new symbols are imported: `from sympy import Symbol` at the top of the file if not already present.
5. Run the test suite for the parsing module:
   ```bash
   pytest sympy/parsing/mathematica/tests/test_parse_mathematica.py
   ```
6. Verify that the previously failing case now passes:
   ```python
   from sympy.parsing.mathematica import parse_mathematica
   assert parse_mathematica('λ') == Symbol('lambda')
   ```
7. Commit the changes and run the full project test suite to ensure no regressions.
8. Update the documentation in `doc/parsing/mathematica.rst` to list the newly supported Greek symbols.

### I5 — Fix parse_mathematica fallback

Update `parse_mathematica` to wrap the parser call in a try/except block. If parsing raises any exception (e.g., SyntaxError for isolated Unicode symbols like "α"), fall back to ``sympify`` to handle simple expressions.

```python
def parse_mathematica(s):
    """
    Translate a string containing a Wolfram Mathematica expression to a SymPy
    expression.
    """
    parser = MathematicaParser()
    try:
        return parser.parse(s)
    except Exception:
        from sympy import sympify
        return sympify(s)
```

## Rules

### R1 — Constraint

All code paths that parse Mathematica expressions must use the updated symbol mapping; existing fallback mechanisms that swallow missing symbols are prohibited to avoid hidden errors.

## References

- `skill_load(name="sympy-sympy-24102", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
