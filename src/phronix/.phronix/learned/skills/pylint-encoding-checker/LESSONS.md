# Lessons — pylint-encoding-checker

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — --notes option ignores punctuation-only tags

**2026-08-21** — The attempt to fix the regex in `pylint/checkers/misc.py` by removing the word‑boundary (\b) did not resolve the issue where tags consisting solely of punctuation (e.g., `???`) are ignored by the `--notes` option. The regex still fails to match punctuation‑only note tags because the word‑boundary prevents a match when the tag contains no word characters. Future fixes should adjust the pattern to explicitly allow such tags, e.g., by expanding the character class or removing the word‑boundary and adding a fallback that matches non‑word note tags.\n\n**Why:** The word‑boundary in the regex prevents matching tags that are only punctuation, so `# ???:` is not captured.\n\n**How to apply:** Update `regex_string` construction in `EncodingChecker` to include a pattern that matches punctuation‑only note tags, such as adding `[\p{Punct}]+` or a permissive alternative.
