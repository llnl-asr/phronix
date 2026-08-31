# Lessons — psf-requests-3362

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — iter_content decode_unicode behavior

**2026-08-31** — iter_content with decode_unicode=True does not guarantee Unicode strings; it yields bytes unless manually decoded. Custom decoding may break other functionality.
