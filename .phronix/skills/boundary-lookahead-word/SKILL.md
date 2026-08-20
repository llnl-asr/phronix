---
name: boundary-lookahead-word
description: Research on boundary lookahead word. Covers what regex pattern correctly matches note tags that end in non-word characters; has this issue been fixed upstream in a later version, and what was the exact solution; are there alternative regex patterns besides positive lookahead that would work. Approaches tried: pr_5859_positive_lookahead, negative_lookahead_non_word, positive_lookahead_non_word_or_eol, remove_word_boundary_entirely.
subject: boundary-lookahead-word
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to boundary lookahead word |
| `X1` | References | Tried: pr_5859_positive_lookahead |
| `X2` | References | Tried: negative_lookahead_non_word |
| `X3` | References | Tried: positive_lookahead_non_word_or_eol |
| `X4` | References | Tried: remove_word_boundary_entirely |
| `X5` | References | Tried: conditional_boundary_by_tag_type |
| `X6` | References | Tried: specific_delimiter_character_class |
| `X7` | References | Sources consulted for boundary lookahead word |









## Instructions

### I1 — How to evaluate a change to boundary lookahead word

Figure of merit: **target_tests_passing** (max, target 1.0).

Measured by: Hidden target tests passing (from task-brief.md) - measured as pass/fail where 1.0 = all passing. Validated locally by running: pylint test.py --notes="YES,???" and checking both fixme warnings appear.

Cases differ along: case, separator, tag_type.

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

### X3 — Tried: positive_lookahead_non_word_or_eol

Replace \b with (?=\W|$) positive lookahead to match tags followed by non-word character or end of string. Semantically equivalent to \b for alphanumeric tags while also working for punctuation-only tags.

**Hypothesis**: \b fails for punctuation-only tags because it requires a transition between \w and \W characters. A positive lookahead (?=\W|$) will provide the same boundary check for alphanumeric tags while also matching after punctuation. Would be falsified if (?=\W|$) creates false positives (matching TODOS when looking for TODO) or misses valid cases.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: remove_word_boundary_entirely

Remove \b suffix entirely from regex pattern. REJECTED: Creates false positives where tag strings match as prefixes (YESS matches YES, TODOLIST matches TODO).

**Hypothesis**: Removing \b entirely will match all note tags including punctuation. Would be falsified if this creates false positives where partial tag matches occur (e.g., "YES" matching in "YESS" or "TODO" matching in "TODOLIST").

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: conditional_boundary_by_tag_type

Check each tag for word characters and conditionally apply \b or (?=\W|$). VIABLE but unnecessarily complex - adds tag-by-tag logic when universal (?=\W|$) approach works for all cases.

**Hypothesis**: Using conditional logic to apply \b only to tags containing word characters, and (?=\W|$) to punctuation-only tags, will correctly match all tag types. Would be falsified if the conditional logic misclassifies tags or if it fails to match some valid cases.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: specific_delimiter_character_class

Use specific character class (?:\s|:|$) to match only space, colon, or end of string. REJECTED: Too restrictive - misses valid delimiters like semicolon, comma, parentheses. (?=\W|$) is more general.

**Hypothesis**: Using a specific character class like (?:\s|:|$) to match only space, colon, or end-of-line after tags will correctly match all tags. Would be falsified if valid note tags can be followed by other delimiters (semicolon, comma, etc.) that this pattern doesn't include.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Sources consulted for boundary lookahead word

- Alternative discovered through regex pattern testing - simpler than PR solution
- https://github.com/pylint-dev/pylint/pull/5859 - merged upstream fix by dbrookman
