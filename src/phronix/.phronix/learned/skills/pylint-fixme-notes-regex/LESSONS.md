# Lessons — pylint-fixme-notes-regex

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — --notes tags that are pure punctuation don't trigger W0511

**2026-08-20** — Symptom: `pylint --notes="YES,???"` reports fixme for `# YES: yes` but not `# ???: no`.

Root cause: in `EncodingChecker.open()` (pylint/checkers/misc.py), the regex built from `self.config.notes` always appended a trailing `\b` word-boundary: `rf"#\s*({notes})\b"`. `\b` only matches between a word char and non-word char, so when the note tag is all punctuation (e.g. `???`), there's no word-boundary transition after it and the match fails.

Fix: only append `\b` per-note when the note tag ends in an alphanumeric char; punctuation-ending tags get no boundary assertion, and drop the boundary from the outer wrapper (it's now per-alternative):

```python
notes = "|".join(
    rf"{re.escape(note)}\b" if note[-1].isalnum() else re.escape(note)
    for note in self.config.notes
)
regex_string = rf"#\s*({notes}|{self.config.notes_rgx})"  # no trailing \b
```

Verified: this exact fix made tests/checkers/unittest_misc.py::TestFixme pass 11/11, including test_non_alphanumeric_codetag.
