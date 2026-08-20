# Lessons — pylint-fixme-checker

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — --notes tags that are pure punctuation were silently ignored

**2026-08-19** — Symptom: `pylint --notes="YES,???"` reported W0511 for `# YES: yes` but not `# ???: no` — punctuation-only note tags never triggered a fixme warning.

Root cause: in `pylint/checkers/misc.py`, `EncodingChecker._fixme_pattern` was built as `rf"#\s*({notes})\b"`. `\b` is a word-boundary assertion that only matches between a word char (`\w`) and a non-word char. A tag made entirely of punctuation (e.g. `???`) has no word chars, so `\b` never matches right after it and the whole regex fails.

Fix: replace `\b` with a lookahead `(?=(:|\s|\Z))` in both the `notes_rgx` and plain `notes` branches — matches when the tag is followed by a colon, whitespace, or end of string, regardless of whether the tag itself is alphanumeric or punctuation. Verified against `tests/checkers/unittest_misc.py::TestFixme` (11/11 passed), including the new `test_non_alphanumeric_codetag`.
