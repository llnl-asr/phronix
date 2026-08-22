# Lessons — pylint-fixme-regex

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Fix regex for note tags with punctuation

**2026-08-21** — The original regex `rf"#\s*({notes})\b"` failed to match note tags that end with punctuation (e.g., `# YES:`). Updated to `rf"#\s*({notes})(?=\W|$)"` which ensures a non‑word character or end of string follows the note keyword, allowing pylint to correctly emit W0511 warnings for such tags.
