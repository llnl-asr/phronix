---
name: pylint-dev-pylint-5859
description: The pylint-dev-pylint-5859 subject.
subject: pylint-dev-pylint-5859
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | ChangeLog entry format for bug-fix patches |
| `R2` | Rules | No existing test coverage for notes-rgx anywhere in repo |
| `R3` | Rules | unittest_misc.py TestFixme: plain-tag matching tests to preserve |
| `R4` | Rules | unittest_misc.py TestFixme: boundary/anti-false-positive tests to preserve |
| `R5` | Rules | Root cause: \b fails on punctuation-only note tags |
| `R6` | Rules | Why a plain lookahead beats \b here |
| `X1` | References | misc.py open()/process_tokens() regex construction (source read in full) |
| `X2` | References | Fix location: EncodingChecker.open() regex_string |









## Instructions

## Rules

### R1 — ChangeLog entry format for bug-fix patches

Add a bullet to the root `ChangeLog` file under the current unreleased "What's New in Pylint 2.13.0?" section, following the existing pattern: `* Fix(ed) ... using ``inline-code`` for checker/message names.` then a blank line, then `Closes #<issue>` (2-space indented to align under the bullet). Entries are flat — no "Bug fixes" subsection header; features/fixes/deprecations all live as bullets under the single version header. A doc/whatsnew/VERSION.rst entry is optional for small bug fixes (only required per contribute.rst for "changes other than small bugs"). No CI/hook was found enforcing this — it's a documented human convention (doc/development_guide/contribute.rst lines 78-97), not machine-checked.

### R2 — No existing test coverage for notes-rgx anywhere in repo

Repo-wide grep for "notes-rgx\|notes_rgx" (excluding tmp/research) only matches the option declaration and open()/process_tokens() usage in pylint/checkers/misc.py itself — no test in tests/checkers/unittest_misc.py or tests/functional exercises notes-rgx, @set_config(notes_rgx=...), or the combined-regex branch `regex_string = rf"#\s*({notes}|{self.config.notes_rgx})\b"`. The fix therefore has no pre-existing regression test constraining notes-rgx's current behavior — it can be changed freely there. Do not assume this means notes-rgx is untested by the hidden grading tests though; task-brief.md explicitly warns not to assume absence of visible tests means absence of hidden target tests.

### R3 — unittest_misc.py TestFixme: plain-tag matching tests to preserve

Any change to misc.py's process_tokens()/open() regex construction must preserve these tests:
1. test_absent_codetag: @set_config(notes=[]), notes_rgx unset → no messages. Only checks notes, not notes_rgx, so broadening the early-return guard to also check notes_rgx does not break it.
2. test_other_present_codetag: @set_config(notes=["CODETAG"]) → notes fully replaces the default list ("FIXME","XXX","TODO"), not appends.
3. Plain tag matching + col_offset/args correctness (test_fixme_with_message, test_todo_without_message, test_xxx_without_space, test_without_space_fixme).

### R4 — unittest_misc.py TestFixme: boundary/anti-false-positive tests to preserve

Any change to misc.py's regex construction must also preserve:
- test_xxx_middle: tag must be anchored right after `#\s*`, not found anywhere in the comment text.
- test_dont_trigger_on_todoist: trailing `\b` must remain so "Todoist" doesn't match "TODO".
- test_issue_2321_should_not_trigger / _should_trigger: detection uses tokenize.COMMENT tokens only, never text search over string literals.

### R5 — Root cause: \b fails on punctuation-only note tags

`\b` only matches at a word/non-word transition. When a note tag is entirely punctuation (e.g. `???`) and is followed by non-word text (e.g. `: no`), there is no word/non-word transition at that boundary position, so `\b` fails to match at all — the FIXME-style comment is silently missed. Confirmed empirically: `re.compile(r"#\s*(YES|???)\b", re.I).search("# ???: no")` returns None while `"# YES: yes"` matches. This is why `--notes="YES,???"` misses lines starting with `# ???`.

### R6 — Why a plain lookahead beats \b here

A trailing lookahead like `(?=(:|\s|\Z))` doesn't inspect the character class of the tag's last char at all — it only requires that whatever follows is one of a fixed set (colon, whitespace, or end-of-string). This sidesteps \b's word/non-word-transition requirement entirely, so it works uniformly for alnum tags (FIXME), punctuation-only tags (???), and mixed tags, while still blocking substring false positives like "FIX" matching inside "FIXME2" (next char "M" isn't `:`/whitespace/EOF).

## References

### X1 — misc.py open()/process_tokens() regex construction (source read in full)

pylint/checkers/misc.py:
- options tuple: `notes` (csv, default ("FIXME","XXX","TODO")), `notes-rgx` (string, no default → None/"" when unset).
- open(): `notes = "|".join(re.escape(n) for n in self.config.notes)`; if self.config.notes_rgx: `regex_string = rf"#\s*({notes}|{self.config.notes_rgx})\b"` else `rf"#\s*({notes})\b"`; then `self._fixme_pattern = re.compile(regex_string, re.I)`. Individual `notes` entries are re.escape'd; notes_rgx is spliced in raw as a regex fragment (intentional — it's user-supplied regex).
- process_tokens(): starts with `if not self.config.notes: return` — this guard never checks notes_rgx, so notes-rgx has no effect when notes is empty/falsy. Identified as the likely core bug for #5859 (see approach fix-process_tokens-guard-for-notes-rgx in research approaches).

### X2 — Fix location: EncodingChecker.open() regex_string

The buggy regex is built in `pylint/checkers/misc.py`, `EncodingChecker.open()`, at lines ~122-128 (base commit 182cc539b815). Two `regex_string = rf"..."` assignments (with/without `self.config.notes_rgx`) both end in `\b` and need the same replacement. This checkout uses `self.config.notes` (not `self.linter.config.notes` — that's an unrelated later refactor, do not copy it in).
