# Lessons — pylint-fixme-checker

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — --notes with punctuation-only tags (e.g. "???") silently ignored

**2026-08-20** — Symptom: `pylint --notes="YES,???"` reports fixme (W0511) for "YES" comments but not "???" comments.

Root cause: in `pylint/checkers/misc.py` `EncodingChecker.open()`, the regex built from `self.config.notes` ended every tag alternative with `\b` (word boundary), applied uniformly. `\b` only matches between a word char and non-word char, so it never matches after a tag that ends in punctuation (e.g. "???") — the alternative can never fire.

Fix: apply `\b` per-tag, conditional on whether the tag's last char is alphanumeric (`note[-1].isalnum()`), not once at the end of the whole alternation group. Tags ending in punctuation get no trailing boundary assertion; alphanumeric tags keep it (needed so "YES" doesn't match inside "YESTERDAY").

```python
notes = "|".join(
    re.escape(note) + r"\b" if note[-1].isalnum() else re.escape(note)
    for note in self.config.notes
)
regex_string = rf"#\s*({notes})"  # trailing \b removed from the outer group
```

Verified: fixed all 11 tests in tests/checkers/unittest_misc.py::TestFixme (10 regression + 1 target), no regressions.
