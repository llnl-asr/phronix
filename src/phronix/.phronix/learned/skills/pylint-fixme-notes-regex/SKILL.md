---
name: pylint-fixme-notes-regex
description: How to fix pylint's fixme/--notes checker (W0511) so punctuation-only note tags like "???" are matched, without breaking word-boundary matching for alphanumeric tags.
subject: pylint-fixme-notes-regex
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Root cause: trailing \b breaks punctuation-only --notes tags |
| `I2` | Instructions | Fix: make \b conditional per-tag, not on the whole alternation |



## Instructions

### I1 — Root cause: trailing \b breaks punctuation-only --notes tags

`pylint --notes="YES,???"` reports W0511 for `# YES: yes` but silently skips `# ???: no`. In `pylint/checkers/misc.py`, `EncodingChecker.open()` builds the fixme regex and always appends one trailing `\b` after the whole alternation of note tags. `\b` only matches at a word/non-word transition, so a tag that is entirely punctuation (e.g. `???`) has no such transition right after it, and the whole compiled pattern fails to match that line at all.

### I2 — Fix: make \b conditional per-tag, not on the whole alternation

In `EncodingChecker.open()`, append `\b` per-tag only when the tag's last char is alnum or `_`; drop the blanket trailing `\b` on the notes alternation (keep it on `notes_rgx` alone, since that's user regex):

```python
notes = "|".join(
    re.escape(note) + (r"\b" if note[-1].isalnum() or note[-1] == "_" else "")
    for note in self.config.notes
)
if self.config.notes_rgx:
    regex_string = rf"#\s*({notes}|{self.config.notes_rgx}\b)"
else:
    regex_string = rf"#\s*({notes})"
```

Verified against `tests/checkers/unittest_misc.py::TestFixme`: fixes `test_non_alphanumeric_codetag`, keeps all other 10 cases passing (11/11 total).

## Rules

## References
