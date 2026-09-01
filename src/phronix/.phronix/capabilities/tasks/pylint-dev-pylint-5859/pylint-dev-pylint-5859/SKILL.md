---
name: pylint-dev-pylint-5859
description: Fix --notes option to handle punctuation-only note tags like ???
subject: pylint-dev-pylint-5859
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |
| `I6` | Instructions | The patch that made the tests pass |

## Instructions

### I1 — What problem it solves

When a user specifies --notes with punctuation-only tags (e.g., --notes="YES,???"), pylint should report W0511 fixme warnings for lines tagged with those punctuation markers (e.g., "# ???: no"), but currently only reports warnings for alphanumeric tags. The symptom: a user configures --notes with punctuation-only patterns, and those tags on code lines fail to trigger the expected fixme warning, while the same config with alphanumeric tags works fine.

### I2 — The key idea

The regex word boundary \b does not work correctly for tags entirely composed of punctuation characters. In regex, \b matches between a word character and a non-word character, but when all characters are non-word (punctuation), there is no word boundary. The fix changes the look-ahead from \b to (?=\s|\W|$), which correctly matches when the position is followed by whitespace, a non-word character, or end of string.

### I3 — Instructions to solve it

1. File: pylint/checkers/misc.py
2. Function: EncodingChecker method building the regex pattern
3. Locate the regex pattern construction for note tag matching (around lines 117-126)
4. In both code paths (when self.config.notes_rgx is set and when it is not), remove the \b word boundary from the end of the regex pattern.
5. Change line 119 (notes_rgx path): from `regex_string = rf"#\s*({notes}|{self.config.notes_rgx})\b"` to `regex_string = rf"#\s*({notes}|{self.config.notes_rgx})"`
6. Change line 122 (else path): from `regex_string = rf"#\s*({notes})\b"` to `regex_string = rf"#\s*({notes})"`
7. Verify the _fixme_pattern compilation still works with re.I flag for case-insensitive matching.
8. Test that both alphanumeric tags (FIXME, TODO, XXX) and punctuation-only tags (???, ?) now correctly trigger W0511 warnings.

### I4 — Constraints and rules

- Must not break the critical regression guard test test_dont_trigger_on_todoist which ensures non-note-tag comments (like Todoist API: comments) do NOT trigger W0511 warnings.
- Must preserve backward compatibility: normal word-based note tags (FIXME, TODO, XXX) must still trigger warnings correctly.
- The fix must handle both alphanumeric tags and punctuation-only tags (like ???, ?).
- Do NOT modify any test files - only modify source code in pylint/checkers/misc.py.
- The regex change must work for all cases: tags at end of line, tags followed by text, tags followed by whitespace, and punctuation-only tags.

### I5 — Pitfalls and lessons

Attempt 1 that simply removed \b broke test_dont_trigger_on_todoist because the broader regex pattern without \b also matched non-note-tag comments like "# Todoist API: What is this task about?" which should NOT trigger warnings.
- The fix must be precise: only remove \b from the note tag pattern, not change the overall matching logic.
- The successful approach (attempt 2) showed that removing \b while keeping the rest of the pattern intact works correctly because the note tags themselves (FIXME, XXX, TODO, or user-specified) are specific enough strings that they won't match arbitrary comments like Todoist API lines.
- Key learning: The \b was the root cause for punctuation tags failing, but its removal is safe because the note tag strings themselves act as sufficient guards against false positives - they only match when the exact tag text appears.

### I6 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/pylint/checkers/misc.py b/pylint/checkers/misc.py
index 69149e61..f3c5b1c4 100755
--- a/pylint/checkers/misc.py
+++ b/pylint/checkers/misc.py
@@ -121,9 +121,9 @@ class EncodingChecker(BaseChecker):
 
         notes = "|".join(re.escape(note) for note in self.config.notes)
         if self.config.notes_rgx:
-            regex_string = rf"#\s*({notes}|{self.config.notes_rgx})\b"
+            regex_string = rf"#\s*({notes}|{self.config.notes_rgx})(?=\s|\W|$)"
         else:
-            regex_string = rf"#\s*({notes})\b"
+            regex_string = rf"#\s*({notes})(?=\s|\W|$)"
 
         self._fixme_pattern = re.compile(regex_string, re.I)
```

## Rules
