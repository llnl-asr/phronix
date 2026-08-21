---
name: pylint-fixme-notes-regex-boundary
description: Research on pylint fixme notes regex boundary. Covers why does the current regex `#\s*({notes})\b` fail to match when a note tag is entirely punctuation, and what regex/matching change (e.g. replacing \b with a lookahead like (?=\W|$) or checking non-word-char/end-of-string) correctly handles punctuation-only, mixed, and alnum tags without breaking the existing \b behavior for alnum tags; does the fix need to change how the matched tag text and trailing message are extracted/reported (the regex match groups feeding into the W0511 message), or is only the boundary condition broken while extract
subject: pylint-fixme-notes-regex-boundary
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to pylint fixme notes regex boundary |
| `I2` | Instructions | How to solve pylint fixme notes regex boundary |
| `I3` | Instructions | Fallback approaches for pylint fixme notes regex boundary |
| `I4` | Instructions | Steps to solve pylint fixme notes regex boundary |
| `X1` | References | Tried: reproduce-via-pylint-cli-in-worktree-venv |
| `X2` | References | Tried: conditional-word-boundary-in-notes-regex |
| `X3` | References | Tried: strip-trailing-boundary-entirely |
| `X4` | References | Tried: conditional-word-boundary-per-note |
| `X5` | References | Tried: unconditional-remove-trailing-boundary |
| `X6` | References | Tried: tokenizer-or-cli-parsing-bug |
| `X7` | References | Tried: per-note-conditional-boundary |
| `X8` | References | Tried: lookahead-non-alnum-terminator |
| `X9` | References | Sources consulted for pylint fixme notes regex boundary |
| `X10` | References | What has been investigated about pylint fixme notes regex boundary |
















## Instructions

### I1 — How to evaluate a change to pylint fixme notes regex boundary

Figure of merit: **fixme_detection_accuracy** (max, target 1.0).

Measured by: Run pylint's fixme checker (via pylint --notes=&lt;tag-list&gt; on a snippet, or by calling MiscChecker._check_note_comment directly) against each corpus instance's source snippet and note-tag config; score 1 if W0511 is reported exactly on the expected lines with the expected tag text, and 0 otherwise (missed match, false match, or wrong tag text extracted). FOM is the fraction of held-out (test-

Cases differ along: multiple_tags_same_line, position_in_comment, should_match, tag_composition, tag_source, trailing_context.

### I2 — How to solve pylint fixme notes regex boundary

Try these in order, ONE at a time. Ranked by measured **fixme_detection_accuracy** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A5` **conditional-word-boundary-per-note** — fixme_detection_accuracy 1.000, validated — Fix: in EncodingChecker.open() (pylint/checkers/misc.py), build the fixme regex with a per
2. `A2` **reproduce-via-pylint-cli-in-worktree-venv** — fixme_detection_accuracy unmeasured, potential — REFUTED (environment-blocked, not a finding about the bug itself). Attempted to run the ac

...and 6 lower-ranked approach(es); see `research_rank`.

### I3 — Fallback approaches for pylint fixme notes regex boundary

If the leading approach fails, these were also measured, ranked by the same metric.

**`A3` per-note-conditional-boundary** — fixme_detection_accuracy unmeasured
  1. `probe_find_call_sites(...)`
  2. `probe_apply_text_replacement(...)`
  3. `probe_run_python_snippet(...)`
  4. `probe_run_pytest_selection(...)`
  5. Add/adjust functional test fixture if needed (judgement)

**`A8` lookahead-non-alnum-terminator** — fixme_detection_accuracy unmeasured
  1. `probe_find_call_sites(...)`
  2. `probe_apply_text_replacement(...)`
  3. `probe_run_python_snippet(...)`
  4. `probe_run_pytest_selection(...)`## Rules

### I4 — Steps to solve pylint fixme notes regex boundary

The steps that solve pylint fixme notes regex boundary, in order. Run them.

1. `probe_find_call_sites(...)` — Locate regex construction
2. `probe_apply_text_replacement(...)` — Replace shared trailing boundary with per-note conditional boundary
3. `probe_run_python_snippet(...)` — Verify no substring false positives / punctuation now matches
4. `probe_run_pytest_selection(...)` — Run existing pylint test suite for fixme checker
5. **Author synthetic instances covering declared dimensions and record trials** (judgement — no tool for this)
   For dimensions not directly exercised by existing pytest cases (tag_composition, trailing_context, tag_source, multiple_tags_same_line, position_in_comment), add instances via research_add_instances/r

## References

### X1 — Tried: reproduce-via-pylint-cli-in-worktree-venv

REFUTED (environment-blocked, not a finding about the bug itself). Attempted to run the actual pylint CLI end-to-end (`pylint test.py --notes="YES,???" --disable=all --enable=fixme`) in this worktree's venv. Failed with ModuleNotFoundError: No module named 'imp' inside astroid/interpreter/_import/sp

**Hypothesis**: Running the real pylint CLI would give an authoritative end-to-end repro of the W0511 fixme miss. Falsified before completion: the venv's Python 3.13 + astroid's `import imp` incompatibility raises ModuleNotFoundError before pylint even runs, unrelated to the reported bug.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: conditional-word-boundary-in-notes-regex

Per-note \b only when note ends in alnum/_; punctuation-ending notes skip \b, fixing failure to match e.g. '???' as note tag

**Hypothesis**: The bug is that misc.py wraps the whole notes alternation with a single trailing \b, which never matches when a note is entirely punctuation (no word-char boundary exists). Moving \b to be conditional per-note (only appended when note[-1] is alnum/_) fixes punctuation tags while preserving existing alnum-tag boundary behavior. False if regex still fails to match '???' or if it introduces false pos

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: strip-trailing-boundary-entirely

Considered simply removing the trailing \b from the regex construction entirely (no per-note conditional) rather than making it conditional per-note.

**Hypothesis**: Unconditionally dropping \b would fix punctuation tags too, but would let alnum note tags match as substrings inside longer words (e.g. notes=TODO would incorrectly match inside TODOLIST) — a real behavior regression not requested by the issue.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: conditional-word-boundary-per-note

Fix: in EncodingChecker.open() (pylint/checkers/misc.py), build the fixme regex with a per-note conditional trailing \b — append \b only when the note tag's last char is alnum or underscore; omit it for tags ending in punctuation. Replaces the current code that appends a single \b to the whole alter

**Hypothesis**: The bug is that \b is an impossible constraint immediately after a non-word char followed by another non-word char, so punctuation-only note tags (e.g. ???) never match; making \b conditional per-tag (only for tags ending in a word char) should fix punctuation tags while preserving word-boundary behavior for word-ending tags like TODO/FIXME. Falsified if any existing TestFixme case starts failing 

**Status**: validated (train 16/16, validate 1/1). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: unconditional-remove-trailing-boundary

Rejected fix: simply drop the trailing \b entirely from the fixme regex (no boundary check at all). This does fix punctuation-only tags but breaks test_dont_trigger_on_todoist — without \b, the "TODO" tag matches inside "Todoist" in "# Todoist API: ...", which the existing test explicitly forbids. T

**Hypothesis**: Refuted: removing \b unconditionally causes false-positive fixme matches on words that merely contain a note tag as a substring (e.g. TODO inside Todoist), confirmed via regex simulation of test_dont_trigger_on_todoist.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: tokenizer-or-cli-parsing-bug

Rejected hypotheses considered and ruled out early: (1) that the bug is in comment_text/token extraction in process_tokens rather than the regex; (2) that --notes CLI CSV parsing mangles punctuation-only tags like "???" before they reach self.config.notes. Both ruled out by reasoning/inspection — th

**Hypothesis**: Refuted: comment token extraction is unaffected (unrelated code path), and CSV parsing of --notes correctly produces "???" in self.config.notes with no mangling — confirmed by reasoning through the "type": "csv" option handling with no contrary evidence found.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: per-note-conditional-boundary

In pylint/checkers/misc.py EncodingChecker.open(), replace the single shared trailing \b appended to the whole notes alternation with a per-note conditional \b: only append \b to a note's escaped pattern when the note's last character is alphanumeric. Punctuation-only notes (e.g. '???') get no trail

**Hypothesis**: The root cause is `rf"#\s*({notes})\b"` applying one \b after the whole alternation group; when a note ends in punctuation, \b requires a word/non-word transition that can't occur there. Making \b conditional per-note (only for alnum-ending notes) should be true if punctuation notes then match and alnum notes still avoid substring false positives (e.g. TODO not matching inside TODOLIST); false if 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: lookahead-non-alnum-terminator

In pylint/checkers/misc.py EncodingChecker.open(), replace the trailing `\b` with a lookahead `(?=[^A-Za-z0-9]|$)` applied once to the whole alternation group (no per-note branching needed). This lookahead means 'next char is not alphanumeric, or end of string', which achieves the same substring-avo

**Hypothesis**: A single regex-wide lookahead replacing \b is simpler than per-note conditional logic and produces equivalent behavior: true if it matches punctuation notes and still rejects TODO-inside-TODOLIST; false if it changes behavior for any existing alnum note case (e.g. notes followed by underscore, which \b treats as non-boundary but this lookahead also treats as blocking since _ is not in [^A-Za-z0-9]

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Sources consulted for pylint fixme notes regex boundary

- pylint/checkers/misc.py EncodingChecker.open(), base commit 182cc539b815, lines ~119-128
- pylint/checkers/misc.py EncodingChecker.open(), lines ~119-128, base commit 182cc539b815; verified directly via Python re module against '# YES: yes', '# ???: no', and TODO/TODOLIST substring case
- pylint/checkers/misc.py EncodingChecker.open(), lines ~119-128; verified via python3 re module against '# YES: yes', '# ???: no', TODO/TODOLIST, and end-of-line cases
- tmp/research/aspect-locate.md — root-cause analysis of pylint/checkers/misc.py EncodingChecker.open(), lines ~119-128 (base commit 182cc539b815)

### X10 — What has been investigated about pylint fixme notes regex boundary

Ground already covered by research on this subject.

- **regex_construction_fix** — Why does the current regex `#\s*({notes})\b` fail to match when a note tag is entirely punctuation, and what regex/matching change (e.g. replacing \b with a lookahead like (?=\W|$) or checking non-wor
  Looked in: pylint/checkers/misc.py around lines 118-130 (_build_notes_pattern/open method) and 150-185 (process_module/_check_note_comment)
- **capture_group_and_message_text** — Does the fix need to change how the matched tag text and trailing message are extracted/reported (the regex match groups feeding into the W0511 message), or is only the boundary condition broken while
  Looked in: pylint/checkers/misc.py process_module / process_tokens where match.group() is used to build the fixme message
- **existing_test_coverage_for_notes** — What do the repository's existing tests (tests/checkers/unittest_misc.py or similar) already assert about --notes and --notes-rgx behavior, and do any of them encode assumptions (e.g. relying on \b) t
  Looked in: tests directory, read-only for understanding expected behavior, not for editing

...and 2 more line(s) of ground covered.
