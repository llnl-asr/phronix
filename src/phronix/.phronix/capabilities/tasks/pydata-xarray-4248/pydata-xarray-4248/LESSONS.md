# Lessons — pydata-xarray-4248

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Units display change breaks test representation

Attempt to show units in dataset overview by modifying summarize_variable failed because the test expects a specific string format; the added units string changes the representation and does not match expected output.

## Lessons

### L1 — Pitfalls and lessons

**2026-08-31** — - Attempt 1 fixed only the import error; higher‑level functionality still failed because the underlying API mismatch remained.
- Attempt 2 introduced a dtype‑mismatch regression; adding error handling without aligning dtypes broke `test_dtype_check`.
- Attempt 3’s performance optimisation increased memory usage, causing intermittent OOM in `test_performance`.
- Changing only the formatting function without adding unit attributes to variables leaves the representation unchanged.
- Forgetting to run the specific repr tests after the patch can let regressions slip through.
- Modifying unrelated parts of the library (e.g., other formatting helpers) can break backwards compatibility.
