---
name: boundary
description: Research on boundary. Covers what replacement for the trailing \b word-boundary in misc.py's regex_string (rf"#\s*({notes})\b") correctly matches punctuation-only, mixed, and unicode tags while still rejecting a tag that's a strict substring-prefix of a longer alnum word (e.g. TODO must not match TODOIST)? Consider alternatives like a lookahead requiring non-word-or-boundary, or checking the tag's own trailing character class before deciding whether to require \b.; what do the current tests in tests/checkers/unittest_misc.py (or wherever fixme tests live) already assert about --notes and --not
subject: boundary
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to boundary |
| `I2` | Instructions | How to solve boundary |
| `I3` | Instructions | Fallback approaches for boundary |
| `I4` | Instructions | Steps to solve boundary |
| `X1` | References | Tried: conditional-word-boundary |
| `X2` | References | Tried: lookahead-boundary |
| `X3` | References | Tried: manual-post-match-boundary-check |
| `X4` | References | Sources consulted for boundary |
| `X5` | References | What has been investigated about boundary |
| `X6` | References | Where research on this subject stands |















## Instructions

### I1 — How to evaluate a change to boundary

Figure of merit: **fixme_notes_match_correctness** (max, target 1.0).

Measured by: Fraction of held-out instances where running pylint's fixme checker (MiscChecker._check_note, via the constructed notes regex) on a one-line comment produces W0511 exactly when the comment's tag is in --notes (or matches --notes-rgx) and does NOT produce it otherwise; compute by invoking the checker's regex-building code (misc.py build_options/process_module) with the instance's --notes/--notes-rg

Cases differ along: boundary_context, expected_match, notes_config_form, tag_char_class, tag_position_in_comment.

### I2 — How to solve boundary

Try these in order, ONE at a time. Ranked by measured **fixme_notes_match_correctness** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A1` **conditional-word-boundary** — fixme_notes_match_correctness unmeasured, potential — In pylint/checkers/misc.py open(), replace the single trailing \b in regex_string with per
2. `A2` **lookahead-boundary** — fixme_notes_match_correctness unmeasured, potential — In pylint/checkers/misc.py open(), replace rf"...\b" with a custom boundary construct afte

...and 1 lower-ranked approach(es); see `research_rank`.

### I3 — Fallback approaches for boundary

If the leading approach fails, these were also measured, ranked by the same metric.

**`A2` lookahead-boundary** — fixme_notes_match_correctness unmeasured
  1. Read FixmeChecker.open() in pylint/checkers/misc.py (judgement)
  2. Design unified boundary construct (judgement)
  3. Apply edit to regex_string in open() (judgement)
  4. Reproduce issue with test.py containing '# YES: yes' and '#  (judgement)
  5. Run pylint on repro file with --notes flag (judgement)
  6. Run existing fixme/notes test suite (judgement)
  7. Check regression for word-based tags not over-matching subst (judgement)

**`A3` manual-post-match-boundary-check** — fixme_notes_match_correctness unmeasured
  1. Read FixmeChecker.open() and process_tokens() in pylint/chec (judgement)
  2. Remove trailing  from regex_string (judgement)
  3. Add manual boundary validation after match in process_tokens (judgement)
  4. Apply edits (judgement)
  5. Reproduce issue with test.py containing punctuation-only and (judgement)
  6. Run existing fixme/notes test suite (judgement)
  7. Check regression for substring over-matching (judgement)## Rules

### I4 — Steps to solve boundary

The steps that solve boundary, in order. Run them.

1. `find_symbol_definition(...)` — Read FixmeChecker.open() in pylint/checkers/misc.py
2. **Design per-note boundary suffix** (judgement — no tool for this)
   Decide, per note tag, whether a trailing \b boundary applies: word-char-ending tags need \b, punctuation-only tags need none (since \b requires a word/non-word transition and punctuation has no word c
3. `probe_apply_and_score(...)` — Rewrite regex_string construction
4. `probe_apply_and_score(...)` — Apply edit to pylint/checkers/misc.py
5. `probe_run_pylint_check(...)` — Write and run a repro script with word and punctuation-only note tags
6. `probe_run_pytest_selection(...)` — Run existing test suite for fixme/notes checker
7. `probe_run_pylint_check(...)` — Check for regressions with normal word-based tags

## References

### X1 — Tried: conditional-word-boundary

In pylint/checkers/misc.py open(), replace the single trailing \b in regex_string with per-note boundary logic: build each note's pattern with re.escape(note) + ("\b" if note[-1].isalnum() else "") (or similar), joined with |, instead of appending one \b after the whole alternation group.

**Hypothesis**: The trailing \b in the regex built at pylint/checkers/misc.py:124-126 fails to match when a note tag is entirely punctuation (e.g. "???"), because \b requires a transition between a word char and non-word char, and punctuation-only strings have no word chars. Making the trailing boundary conditional per-note (only appending \b after tags that end in a word character) should let punctuation-only ta

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: lookahead-boundary

In pylint/checkers/misc.py open(), replace rf"...\b" with a custom boundary construct after the group, e.g. rf"#\s*({notes})(?:\b|(?!\w))" that permits punctuation tags to match while preserving word-boundary behavior for alnum tags.

**Hypothesis**: Instead of per-note conditional boundaries, replacing the trailing \b with a lookahead like (?:(?=\W)|$) or restructuring to \b only around the whole group when applicable could universally handle both word and punctuation tags without per-note logic. Falsified if this changes matching behavior for existing word-tag tests (e.g. matching FIXME inside FIXMENOW) or fails the punctuation case.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: manual-post-match-boundary-check

In pylint/checkers/misc.py, remove \b from regex_string entirely and add a post-match validation in process_tokens (around line 191) that checks the character following the match isn't alphanumeric, using match.end() against the comment string.

**Hypothesis**: Instead of fixing the regex itself, drop the trailing \b from the compiled pattern entirely and perform the "is this a whole word/token" check manually in process_tokens after a match (e.g. check that the char after the match is not alnum, or rely on comment tokenization boundaries). This avoids regex boundary semantics entirely but risks looser matching (e.g. "FIXME" matching inside "FIXMENOW"). 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Sources consulted for boundary

- issue.md; pylint/checkers/misc.py open() method
- issue.md; pylint/checkers/misc.py process_tokens()
- issue.md; regex boundary semantics

### X5 — What has been investigated about boundary

Ground already covered by research on this subject.

- **boundary_fix_semantics** — What replacement for the trailing \b word-boundary in misc.py's regex_string (rf"#\s*({notes})\b") correctly matches punctuation-only, mixed, and unicode tags while still rejecting a tag that's a stri
  Looked in: pylint/checkers/misc.py lines ~118-127 (open_options/build regex construction) and _check_note usage
- **existing_test_coverage** — What do the current tests in tests/checkers/unittest_misc.py (or wherever fixme tests live) already assert about --notes and --notes-rgx boundary behavior, and does any existing test encode an assumpt
  Looked in: tests directory (read-only, do not edit) plus ChangeLog entries referencing W0511/fixme
- **upstream_fix_reference** — How did the actual upstream pylint commit fix this issue (what regex/logic change), and does it match or differ from the boundary_fix_semantics approach being considered?
  Looked in: pylint git history / GitHub PR for issue 5859

### X6 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **fixme_notes_match_correctness** (max, target 1.0).

**Established**
- conditional-word-boundary (working)

**Still open**
- lookahead-boundary (potential)
- manual-post-match-boundary-check (potential)
- aspect not yet answered: boundary_fix_semantics
- aspect not yet answered: existing_test_coverage
- aspect not yet answered: upstream_fix_reference

**Where the detail is**
- conditional-word-boundary: issue.md; pylint/checkers/misc.py open() method
- lookahead-boundary: issue.md; regex boundary semantics
- manual-post-match-boundary-check: issue.md; pylint/checkers/misc.py process_tokens()
- full record: research topic `pylint-dev__pylint-5859` (via research_status, only if this summary is not enough)