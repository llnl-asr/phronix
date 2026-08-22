---
name: pylint-dev-pylint-5859
description: Fix pylint's --notes fixme checker so punctuation-only note tags (e.g. "???") are detected, not just alphanumeric ones like TODO/FIXME.
subject: pylint-dev-pylint-5859
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem: --notes ignores punctuation-only note tags (fixme checker) |
| `I2` | Instructions | Steps to solve: replace trailing \b with a lookahead |



## Instructions

### I1 — Problem: --notes ignores punctuation-only note tags (fixme checker)

`pylint --notes="YES,???"` reported W0511 (fixme) for `# YES: yes` but silently
ignored `# ???: no`. The note tag `???` is entirely punctuation (no word
characters), and the checker's regex ended in `\b` (word-boundary), which only
fires at a transition between a word char and a non-word char — it can never
match right after a tag with no word characters in it.

Recognize this problem: a `--notes` tag made only of punctuation/non-word
characters is silently never flagged, while alphanumeric tags (TODO, FIXME)
work fine.

Location: `pylint/checkers/misc.py`, `EncodingChecker._build_regex`, where
`self._fixme_pattern` is built from `self.config.notes`:

```python
notes = "|".join(re.escape(note) for note in self.config.notes)
if self.config.notes_rgx:
    regex_string = rf"#\s*({notes}|{self.config.notes_rgx})\b"
else:
    regex_string = rf"#\s*({notes})\b"
```

### I2 — Steps to solve: replace trailing \b with a lookahead

In `pylint/checkers/misc.py`, replace the trailing `\b` in both branches of
`regex_string` with a lookahead for what legally follows a tag — a colon,
whitespace, or end of string — instead of asserting a word-boundary:

```diff
-            regex_string = rf"#\s*({notes}|{self.config.notes_rgx})\b"
+            regex_string = rf"#\s*({notes}|{self.config.notes_rgx})\s*(?=(:|\s|$))"
-            regex_string = rf"#\s*({notes})\b"
+            regex_string = rf"#\s*({notes})\s*(?=(:|\s|$))"
```

That is the entire fix — a two-line change in one file, no test files touched.

The lookahead is a strict generalization of `\b` for this use: it still
requires the tag be followed by `:`, whitespace, or end-of-string (which is
every case `\b` covered for alphanumeric tags), while also covering the
punctuation-only-tag case `\b` missed.

Verify with `tests/checkers/unittest_misc.py::TestFixme` (targeted, not the
full suite) — target test `test_non_alphanumeric_codetag` must pass, and the
other 10 TestFixme tests must keep passing as regression coverage.

If the CLI (`pylint test.py --notes=...`) errors in the sandbox for unrelated
reasons (e.g. a Python 3.13 compatibility issue), that's not a fix problem —
verify via the unit tests or by testing the built regex directly in a Python
snippet instead of chasing the CLI environment issue.

## Rules

## References
