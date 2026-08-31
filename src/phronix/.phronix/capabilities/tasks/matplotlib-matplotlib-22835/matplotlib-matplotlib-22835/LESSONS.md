# Lessons — matplotlib-matplotlib-22835

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — format_cursor_data truncates float string for BoundaryNorm

**2026-08-29** — Added a try/except for BoundaryNorm invertibility but the format_cursor_data function still returns truncated float strings (e.g., '[-1.]' instead of '[-1.0]'), causing test failure.

### L2 — Pitfalls

**2026-08-29** — - Using a simple fallback that returns the raw normed values (`[0.900]`) changes numeric precision, causing test failures.\n- Re‑using the same `try/except` without adjusting formatting does not resolve the precision mismatch.\n- Adding a comment only (without changing the fallback) does not affect the output format.\n- Attempting to adjust the fallback without preserving the original formatting precision leads to mismatched string representations (e.g., "[-1.]" vs "[-1.0]").
