# Lessons — astropy-astropy-14182

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — RST __init__ missing header_rows support

RST writer __init__ does not accept header_rows; adding **kwargs to __init__ does not propagate to writer, causing TypeError and read failure due to column conversion

## Lessons

### L1 — Attempt 1 & 2 Failed

**2026-08-31** — Adding `**kwargs` without handling `header_rows` caused a `ValueError` during column conversion because the RST writer still did not process the header rows.

### L2 — Attempt 3 Stub Erfa Failure

**2026-08-31** — Attempt 3 introduced a stub `erfa` package lacking required symbols, causing ImportError and preventing the test runner from starting.

### L3 — L1 — Failed header_rows init

**2026-08-31** — Attempt 2 added header_rows support to writer but reading failed: `TypeError: __init__() got an unexpected keyword argument 'header_rows'` in `rst.py`. The fix is to modify RST.__init__ to accept **kwargs and forward header_rows to FixedWidth.

### L4 — L2 — Fixed TypeError in RST writer

**2026-08-31** — Attempted to pass `header_rows` to `RST` writer caused `TypeError: RST.__init__() got an unexpected keyword argument 'header_rows'`. The fix adding `**kwargs` and forwarding `header_rows` resolves the error.

### L5 — L2 — Failure after initial fix

**2026-08-31** — Attempted fix changed __init__ signature without **kwargs, causing TypeError when header_rows was passed. Tests still failing: test_rst_with_header_rows expecting unit conversion.
