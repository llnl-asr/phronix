---
name: lookahead-regex
description: Research on lookahead regex. Covers what regex pattern correctly matches note tags that end in non-word characters; has this issue been fixed upstream in a later version, and what was the exact solution; are there alternative regex patterns besides positive lookahead that would work. Approaches tried: pr_5859_positive_lookahead, negative_lookahead_non_word.
subject: lookahead-regex
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to lookahead regex |
| `I2` | Instructions | How to solve lookahead regex |
| `X1` | References | Tried: pr_5859_positive_lookahead |
| `X2` | References | Tried: negative_lookahead_non_word |
| `X3` | References | Sources consulted for lookahead regex |
| `X4` | References | What has been investigated about lookahead regex |







## Instructions

### I1 — How to evaluate a change to lookahead regex

Figure of merit: **target_tests_passing** (max, target 1.0).

Measured by: Hidden target tests passing (from task-brief.md) - measured as pass/fail where 1.0 = all passing. Validated locally by running: pylint test.py --notes="YES,???" and checking both fixme warnings appear.

Cases differ along: case, separator, tag_type.

### I2 — How to solve lookahead regex

Try these in order. Ranked by measured **target_tests_passing** (max, target 1.0). Each one's hypothesis and evidence is in the matching `Tried:` reference on this skill.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. **pr_5859_positive_lookahead** — target_tests_passing 1.000, potential — Replace \b with positive lookahead (?=:|\s|$) matching colon, whitespace, or end of string
2. **negative_lookahead_non_word** — target_tests_passing 1.000, potential — Replace \b with negative lookahead (?!\w) ensuring next character is not a word character

## Rules

## References

### X1 — Tried: pr_5859_positive_lookahead

Replace \b with positive lookahead (?=:|\s|$) matching colon, whitespace, or end of string

**Hypothesis**: Word boundary \b fails for punctuation-only tags because \b requires a word character on one side. A positive lookahead (?=:|\s|$) explicitly checks for valid separators (colon, whitespace, or string end) without consuming them, allowing punctuation-only tags to match. Falsified if the pattern matches note tags in the middle of words (e.g., "NOTODO" matching "TODO").

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: negative_lookahead_non_word

Replace \b with negative lookahead (?!\w) ensuring next character is not a word character

**Hypothesis**: \b fails because it requires a word character to exist for a boundary. (?!\w) simply asserts the next character is not a word character (or is end of string), which works for both alphanumeric and punctuation-only tags. Falsified if it incorrectly matches tags followed by punctuation that should be part of the tag (though note tags are user-defined so this is less likely).

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Sources consulted for lookahead regex

- Alternative discovered through regex pattern testing - simpler than PR solution
- https://github.com/pylint-dev/pylint/pull/5859 - merged upstream fix by dbrookman

### X4 — What has been investigated about lookahead regex

Ground already covered by research on this subject.

- **regex_boundary** — What regex pattern correctly matches note tags that end in non-word characters?
  Looked in: The regex pattern construction in pylint/checkers/misc.py open() method, specifically the word boundary assertion
- **upstream_solution** — Has this issue been fixed upstream in a later version, and what was the exact solution?
  Looked in: GitHub issue tracker and PR history for pylint-dev/pylint
- **regex_lookahead_alternatives** — Are there alternative regex patterns besides positive lookahead that would work?
  Looked in: Python re module documentation, regex pattern best practices
