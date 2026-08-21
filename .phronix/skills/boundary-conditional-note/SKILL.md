---
name: boundary-conditional-note
description: Superseded — merged into [[pylint-fixme-notes-regex-boundary]] (fixme regex content) and [[sympy-itermonomials]] (stray itermonomials rule). Kept as a pointer only.
subject: boundary-conditional-note
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to boundary conditional note |
| `R2` | Rules | Superseded: load pylint-fixme-notes-regex-boundary and sympy-itermonomials instead |
| `X1` | References | Where research on this subject stands |
| `X11` | References | Tried: conditional-word-boundary-in-notes-regex |
| `X12` | References | Tried: strip-trailing-boundary-entirely |
| `X13` | References | Tried: unconditional-remove-trailing-boundary |
| `X14` | References | Tried: tokenizer-or-cli-parsing-bug |
| `X15` | References | Tried: per-note-conditional-boundary |
| `X16` | References | Tried: lookahead-non-alnum-terminator |
| `X17` | References | Sources consulted for boundary conditional note |




























## Instructions

### I1 — How to evaluate a change to boundary conditional note

Figure of merit: **fixme_detection_accuracy** (max, target 1.0).

Measured by: Run pylint's fixme checker (via pylint --notes=&lt;tag-list&gt; on a snippet, or by calling MiscChecker._check_note_comment directly) against each corpus instance's source snippet and note-tag config; score 1 if W0511 is reported exactly on the expected lines with the expected tag text, and 0 otherwise (missed match, false match, or wrong tag text extracted). FOM is the fraction of held-out (test-

Cases differ along: multiple_tags_same_line, position_in_comment, should_match, tag_composition, tag_source, trailing_context.

## Rules

### R2 — Superseded: load pylint-fixme-notes-regex-boundary and sympy-itermonomials instead

This subject duplicates [[sympy-itermonomials-total-degree]] exactly (same misnamed mix of pylint fixme regex research plus a misfiled itermonomials rule). Load [[pylint-fixme-notes-regex-boundary]] for the fixme regex content and [[sympy-itermonomials#R2]] for the itermonomials total-degree fix instead of this one.

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **fixme_detection_accuracy** (max, target 1.0).

**Established**
- reproduce-via-pylint-cli-in-worktree-venv (potential)
- conditional-word-boundary-in-notes-regex (potential)
- conditional-word-boundary-per-note (working fixme_detection_accuracy=1.0)
- unconditional-remove-trailing-boundary (potential)
- per-note-conditional-boundary (potential)
- lookahead-non-alnum-terminator (potential)

**Still open**
- strip-trailing-boundary-entirely (potential)
- tokenizer-or-cli-parsing-bug (potential)
- aspect not yet answered: regex_construction_fix
- aspect not yet answered: capture_group_and_message_text
- aspect not yet answered: existing_test_coverage_for_notes
- aspect not yet answered: changelog_and_prior_fix_pattern

**Where the detail is**
- reproduce-via-pylint-cli-in-worktree-venv: tmp/research/aspect-reproduce.md
- conditional-word-boundary-in-notes-regex: pylint/checkers/misc.py EncodingChecker.open(), base commit 182cc539b815, lines ~119-128
- strip-trailing-boundary-entirely: tmp/research/aspect-minimal-change.md, "What I ruled out" section
- conditional-word-boundary-per-note: tmp/research/aspect-locate.md — root-cause analysis of pylint/checkers/misc.py EncodingChecker.open(), lines ~

...and 3 more line(s); see the full record.### X10 — Tried: reproduce-via-pylint-cli-in-worktree-venv

REFUTED (environment-blocked, not a finding about the bug itself). Attempted to run the actual pylint CLI end-to-end (`pylint test.py --notes="YES,???" --disable=all --enable=fixme`) in this worktree's venv. Failed with ModuleNotFoundError: No module named 'imp' inside astroid/interpreter/_import/sp

**Hypothesis**: Running the real pylint CLI would give an authoritative end-to-end repro of the W0511 fixme miss. Falsified before completion: the venv's Python 3.13 + astroid's `import imp` incompatibility raises ModuleNotFoundError before pylint even runs, unrelated to the reported bug.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X11 — Tried: conditional-word-boundary-in-notes-regex

Per-note \b only when note ends in alnum/_; punctuation-ending notes skip \b, fixing failure to match e.g. '???' as note tag

**Hypothesis**: The bug is that misc.py wraps the whole notes alternation with a single trailing \b, which never matches when a note is entirely punctuation (no word-char boundary exists). Moving \b to be conditional per-note (only appended when note[-1] is alnum/_) fixes punctuation tags while preserving existing alnum-tag boundary behavior. False if regex still fails to match '???' or if it introduces false pos

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X12 — Tried: strip-trailing-boundary-entirely

Considered simply removing the trailing \b from the regex construction entirely (no per-note conditional) rather than making it conditional per-note.

**Hypothesis**: Unconditionally dropping \b would fix punctuation tags too, but would let alnum note tags match as substrings inside longer words (e.g. notes=TODO would incorrectly match inside TODOLIST) — a real behavior regression not requested by the issue.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X13 — Tried: unconditional-remove-trailing-boundary

Rejected fix: simply drop the trailing \b entirely from the fixme regex (no boundary check at all). This does fix punctuation-only tags but breaks test_dont_trigger_on_todoist — without \b, the "TODO" tag matches inside "Todoist" in "# Todoist API: ...", which the existing test explicitly forbids. T

**Hypothesis**: Refuted: removing \b unconditionally causes false-positive fixme matches on words that merely contain a note tag as a substring (e.g. TODO inside Todoist), confirmed via regex simulation of test_dont_trigger_on_todoist.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X14 — Tried: tokenizer-or-cli-parsing-bug

Rejected hypotheses considered and ruled out early: (1) that the bug is in comment_text/token extraction in process_tokens rather than the regex; (2) that --notes CLI CSV parsing mangles punctuation-only tags like "???" before they reach self.config.notes. Both ruled out by reasoning/inspection — th

**Hypothesis**: Refuted: comment token extraction is unaffected (unrelated code path), and CSV parsing of --notes correctly produces "???" in self.config.notes with no mangling — confirmed by reasoning through the "type": "csv" option handling with no contrary evidence found.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X15 — Tried: per-note-conditional-boundary

In pylint/checkers/misc.py EncodingChecker.open(), replace the single shared trailing \b appended to the whole notes alternation with a per-note conditional \b: only append \b to a note's escaped pattern when the note's last character is alphanumeric. Punctuation-only notes (e.g. '???') get no trail

**Hypothesis**: The root cause is `rf"#\s*({notes})\b"` applying one \b after the whole alternation group; when a note ends in punctuation, \b requires a word/non-word transition that can't occur there. Making \b conditional per-note (only for alnum-ending notes) should be true if punctuation notes then match and alnum notes still avoid substring false positives (e.g. TODO not matching inside TODOLIST); false if 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X16 — Tried: lookahead-non-alnum-terminator

In pylint/checkers/misc.py EncodingChecker.open(), replace the trailing `\b` with a lookahead `(?=[^A-Za-z0-9]|$)` applied once to the whole alternation group (no per-note branching needed). This lookahead means 'next char is not alphanumeric, or end of string', which achieves the same substring-avo

**Hypothesis**: A single regex-wide lookahead replacing \b is simpler than per-note conditional logic and produces equivalent behavior: true if it matches punctuation notes and still rejects TODO-inside-TODOLIST; false if it changes behavior for any existing alnum note case (e.g. notes followed by underscore, which \b treats as non-boundary but this lookahead also treats as blocking since _ is not in [^A-Za-z0-9]

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X17 — Sources consulted for boundary conditional note

- pylint/checkers/misc.py EncodingChecker.open(), base commit 182cc539b815, lines ~119-128
- pylint/checkers/misc.py EncodingChecker.open(), lines ~119-128, base commit 182cc539b815; verified directly via Python re module against '# YES: yes', '# ???: no', and TODO/TODOLIST substring case
- pylint/checkers/misc.py EncodingChecker.open(), lines ~119-128; verified via python3 re module against '# YES: yes', '# ???: no', TODO/TODOLIST, and end-of-line cases
- tmp/research/aspect-locate.md — root-cause analysis of pylint/checkers/misc.py EncodingChecker.open(), lines ~119-128 (base commit 182cc539b815)
