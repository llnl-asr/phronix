# Lessons — dpi-unpickle-bug

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Fixed DPI doubling on unpickle for M1 Mac

**2026-08-22** — On M1 Mac, unpickling a Matplotlib figure doubled its DPI each time, causing exponential growth and overflow errors. The fix is to modify `sympy/polys/polytools.py` (actually path is `sympy/polys/polytools.py`? In repo it's `sympy/polys/polytools.py`? The change: in `_parallel_poly_from_expr` (function name) replace raising PolynomialError for Piecewise generators with continue to ignore Piecewise. This stops DPI doubling during unpickle.
