---
name: punctuation-handling
description: Explanation of why punctuation‑only note tags are not detected by pylint's note handling.
subject: punctuation-handling
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Punctuation-only note tags are ignored |
| `I2` | Instructions | Punctuation-only note tags are recognized |
| `I3` | Instructions | Remove trailing word boundary from notes regex |




## Instructions

### I1 — Punctuation-only note tags are ignored

The `EncodingChecker` builds a regular expression for note tags using `regex_string = rf"#\s*({notes})\b"` (or with `notes_rgx`). The trailing `\b` word‑boundary anchor only matches when the note tag ends with a word character (alphanumeric or underscore). Punctuation‑only tags such as `!!!` contain no word characters, so the `\b` does not match and the comment is not recognised as a note. Consequently, `--notes=!!!` does not trigger a `W0511` warning, and such tags are effectively ignored by pylint.

### I2 — Punctuation-only note tags are recognized

The `EncodingChecker` now builds its regular expression without a word‑boundary anchor (`\\b`). As a result, note tags consisting solely of punctuation (e.g., `???`, `!!!`) are correctly matched when they are listed in the `--notes` option. This change fixes the previous behavior where such tags were ignored because the regex required a trailing word character.

### I3 — Remove trailing word boundary from notes regex

Modify `pylint/checkers/misc.py` to build the regex without a trailing `\b`. Replace:
```python
if self.config.notes_rgx:
    regex_string = rf"#\s*({notes}|{self.config.notes_rgx})\b"
else:
    regex_string = rf"#\s*({notes})\b"
```
with:
```python
if self.config.notes_rgx:
    regex_string = rf"#\s*({notes}|{self.config.notes_rgx})"
else:
    regex_string = rf"#\s*({notes})"
```

## Rules

## References
