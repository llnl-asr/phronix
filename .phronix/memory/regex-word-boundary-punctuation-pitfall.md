---
name: regex-word-boundary-punctuation-pitfall
description: Regex \b word boundary fails for punctuation-only patterns because it requires transition between \w and \W characters
metadata:
  type: lesson
---

**Symptom**: Regex pattern with `\b` matches alphanumeric strings correctly but fails to match punctuation-only strings in the same context.

**Root cause**: `\b` (word boundary) matches at the transition between word characters `\w` (letters, digits, underscore) and non-word characters `\W`. For punctuation-only patterns like "???", there is no such transition - the last character is already `\W`, so `\b` can only match if followed by `\w`, which is the opposite of what boundary checking needs.

**Example**:
- `YES\b` matches "YES:" because 'S' is `\w` and ':' is `\W` (transition exists)
- `\?\?\?\b` does NOT match "???:" because '?' is `\W` and ':' is `\W` (no transition)

**Fix**: Replace `\b` with `(?=\W|$)` (positive lookahead for non-word character or end-of-string). This is semantically equivalent to `\b` for alphanumeric patterns while also working for punctuation-only patterns.

**Why this works**: The lookahead `(?=\W|$)` checks that the next position is either a non-word character OR end-of-string, without requiring a transition from `\w`. For "YES:", both 'S' and the lookahead position satisfy `(?=\W|$)`. For "???:", the '?' and lookahead position also satisfy it.

**Prevention**: When using regex boundaries for patterns that may contain punctuation, use lookahead assertions `(?=\W|$)` instead of word boundaries `\b`.

**Related**: Found in pylint fixme checker (issue #5859) where note tags consisting entirely of punctuation were not being detected.
