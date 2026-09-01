# Lessons — requests-iter-content

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — iter_content with decode_unicode returns bytes

**2026-08-31** — When using `requests.Response.iter_content` with `decode_unicode=True`, the chunks are still returned as bytes, not as unicode strings. The `decode_unicode` flag only affects the conversion of `iter_lines`. Therefore, expecting `next(r.iter_content(..., decode_unicode=True))` to be a string is incorrect; you should decode the bytes yourself or use `r.text`/`iter_lines` for text data.
