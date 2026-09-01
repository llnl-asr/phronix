# Lessons — sympy-sympy-24102

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — The fallback change introduced in attempt 3 caused test `test_parser_m

**2026-08-27** — The fallback change introduced in attempt 3 caused test `test_parser_mathematica_tokenizer` to fail at `chain("α")`. The parser raised a SyntaxError because the tokenization path for a single Unicode character does not produce a valid AST. The fallback to `sympify` only handles simple expressions but the tokenizer still fails, so the test remains failing.
