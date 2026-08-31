# Lessons — pylint-dev-pylint-7228

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Attempting Unicode property escapes fails

**2026-08-29** — Using `\p{Han}` in `function-rgx` caused `re.error: bad escape \p`. Python's standard regex engine cannot compile this, so the change always fails regardless of test coverage. Future attempts should consider using the third‑party `regex` module or limiting to explicit character ranges.
