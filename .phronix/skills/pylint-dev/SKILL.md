---
name: pylint-dev
description: Research on pylint dev. Covers what is the correct replacement for the trailing/leading \b word-boundary assertions in the _fixme_pattern regex (misc.py open(), ~line 122-126) so that both word tags (FIXME, TODO) and all-punctuation tags (???, !!!) match correctly, while still rejecting substring matches like TODOIST for TODO and FIXMENOW for FIXME.
subject: pylint-dev
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to pylint dev |
| `I2` | Instructions | How to solve pylint dev |
| `I3` | Instructions | Fallback approaches for pylint dev |
| `I4` | Instructions | Steps to solve pylint dev |
| `X1` | References | Where research on this subject stands |
| `X5` | References | Tried: per_tag_boundary |
| `X6` | References | Tried: whitespace_or_end_lookaround |
| `X7` | References | Tried: per-tag-boundary-fix-notes-only-leave-notes-rgx-unbounded-as-is |
| `X8` | References | Tried: special_case_notes_rgx_only |
| `X9` | References | Tried: remove_boundary_entirely |
| `X10` | References | Tried: per_tag_boundary_notes_only_keep_notes_rgx_bounded |
| `X11` | References | Tried: uniform_lookahead_boundary_notes_and_notes_rgx |
| `X12` | References | Sources consulted for pylint dev |
| `X13` | References | What has been investigated about pylint dev |





















## Instructions

### I1 — How to evaluate a change to pylint dev

Figure of merit: **fixme_notes_match_accuracy** (max, target 1.0).

Measured by: Fraction of corpus instances where running pylint's fixme checker (MiscChecker._check_encoding / open()+ visit_note via probe_run_pylint_check, or a direct unit invocation of the compiled _fixme_pattern against the comment text) produces a W0511 match exactly when the instance's `expected` field says it should, across all configured --notes / notes-rgx values, including entirely-punctuation tags.

Cases differ along: boundary_context, position_in_comment, should_match, tag_char_class, tag_source.

### I2 — How to solve pylint dev

Try these in order, ONE at a time. Ranked by measured **fixme_notes_match_accuracy** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A2` **conditional-word-boundary** — fixme_notes_match_accuracy unmeasured, potential — Only append (word-boundary) to a note tag's regex alternative when the tag ends in an alph
2. `A4` **apply-same-boundary-fix-to-notes-rgx** — fixme_notes_match_accuracy unmeasured, potential — REFUTED. Applying the same per-tag (word-boundary)-vs-(?!(word-char)) conditional boundary

...and 7 lower-ranked approach(es); see `research_rank`.### I3 — Fallback approaches for pylint dev

If the leading approach fails, these were also measured. Ranked by the same metric.

**`A3` per_tag_boundary_notes_only_keep_notes_rgx_bounded** — fixme_notes_match_accuracy unmeasured
  1. Read EncodingChecker.open() regex construction (judgement)
  2. Build per-tag conditional boundary for literal notes (judgement)
  3. Leave notes_rgx spliced in with its existing trailing \b (judgement)
  4. Verify against issue example (judgement)
  5. Verify against existing functional fixtures (judgement)
  6. Run repository test suite for the checker (judgement)
  7. Judge whether the diff stays minimal and scoped (judgement)

**`A9` uniform_lookahead_boundary_notes_and_notes_rgx** — fixme_notes_match_accuracy unmeasured
  1. Read EncodingChecker.open() regex construction (judgement)
  2. Replace \b with (?!\w) uniformly (judgement)
  3. Verify against issue example (judgement)
  4. Verify notes_rgx boundary semantics unchanged for existing f (judgement)
  5. Judge blast radius on notes_rgx semantics (judgement)
  6. Run repository test suite for the checker (judgement)

### I3 — Fallback approaches for pylint dev

If the leading approach fails, these were also measured, ranked by the same metric.

**`A3` per_tag_boundary_notes_only_keep_notes_rgx_bounded** — fixme_notes_match_accuracy unmeasured
  1. Read EncodingChecker.open() regex construction (judgement)
  2. Build per-tag conditional boundary for literal notes (judgement)
  3. Leave notes_rgx spliced in with its existing trailing (word- (judgement)
  4. Verify against issue example (judgement)
  5. Verify against existing functional fixtures (judgement)
  6. Run repository test suite for the checker (judgement)
  7. Judge whether the diff stays minimal and scoped (judgement)

**`A9` uniform_lookahead_boundary_notes_and_notes_rgx** — fixme_notes_match_accuracy unmeasured
  1. Read EncodingChecker.open() regex construction (judgement)
  2. Replace (word-boundary) with (?!(word-char)) uniformly (judgement)
  3. Verify against issue example (judgement)
  4. Verify notes_rgx boundary semantics unchanged for existing f (judgement)
  5. Judge blast radius on notes_rgx semantics (judgement)
  6. Run repository test suite for the checker (judgement)## Rules

### I4 — Steps to solve pylint dev

The steps that solve pylint dev, in order. Run them.

1. `probe_read_file_region(...)` — Read EncodingChecker.open() regex construction
2. `probe_apply_and_score(...)` — Build per-tag conditional boundary for literal notes
3. `probe_apply_and_score(...)` — Leave notes_rgx spliced in with its existing trailing boundary
4. `probe_run_pylint_check(...)` — Verify against issue example
5. `probe_run_pytest_selection(...)` — Verify against existing functional fixtures
6. `probe_run_pytest_selection(...)` — Run repository test suite for the checker
7. **Judge whether the diff stays minimal and scoped** (judgement — no tool for this)
   Confirm the change is confined to EncodingChecker.open()'s regex-building code and does not alter notes_rgx semantics, matching the minimal-diff spirit of the actual bug.

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **fixme_notes_match_accuracy** (max, target 1.0).

**Established**
- conditional-word-boundary (working)
- apply-same-boundary-fix-to-notes-rgx (potential)
- per_tag_boundary (potential)
- per-tag-boundary-fix-notes-only-leave-notes-rgx-unbounded-as-is (potential)
- per_tag_boundary_notes_only_keep_notes_rgx_bounded (potential)
- uniform_lookahead_boundary_notes_and_notes_rgx (potential)

**Still open**
- whitespace_or_end_lookaround (potential)
- special_case_notes_rgx_only (potential)
- remove_boundary_entirely (potential)

**Where the detail is**
- conditional-word-boundary: pylint/checkers/misc.py EncodingChecker.open() lines ~119-128; verified via CheckerTestCase-style direct check
- apply-same-boundary-fix-to-notes-rgx: tmp/research/aspect-notes-rgx-interaction.md; tests/functional/f/fixme.rc, fixme.py, fixme.txt
- per_tag_boundary: Own analysis of pylint/checkers/misc.py:119-128 plus pylint-dev/pylint#5859 issue examples using ???/!!! note 
- whitespace_or_end_lookaround: Own analysis during regex_fix_strategy investigation of pylint/checkers/misc.py
- per-tag-boundary-fix-notes-only-leave-notes-rgx-unbounded-as-is: tmp/research/aspect-notes-rgx-interaction.md

...and 2 more line(s); see the full record.### X4 — Tried: apply-same-boundary-fix-to-notes-rgx

REFUTED. Applying the same per-tag \b-vs-(?!\w) conditional boundary logic to notes_rgx (or naively removing \b from the whole shared regex) is not viable: notes_rgx is a free-form user regex, not a literal string, so "last character of the tag" isn't statically inspectable to choose \b vs (?!\w). A

**Hypothesis**: If the \b boundary bug affects --notes for punctuation tags, removing/uniformly changing \b across the whole alternation (notes | notes_rgx) would fix --notes-rgx the same way without regressing anything.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: per_tag_boundary

Build the trailing \b per-alternative instead of once for the whole regex group: append \b to a note tag only if it ends in a word char (re.search(r"\w$", note)); punctuation-only tags (e.g. ???, !!!) get no boundary assertion. Applied to EncodingChecker.open() in pylint/checkers/misc.py.

**Hypothesis**: A single shared \b after the whole alternation group can never match right after an all-punctuation tag (since both sides of that position are \W, and \b requires a \w/\W transition), so punctuation-only tags never trigger W0511 regardless of context. Moving \b to apply per-tag, conditioned on whether that tag ends in a word char, fixes punctuation tags while preserving the substring-rejection beh

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: whitespace_or_end_lookaround

REFUTED (not built/measured). Replace the trailing \b with a lookaround like (?:\b|(?=\s)|$) applied once to the whole alternation group, instead of per-tag.

**Hypothesis**: Hypothesized that a single global boundary assertion combining \b with a whitespace/end lookahead could substitute for \b and fix punctuation tags without per-tag logic. Refuted by inspection before building: \s is itself \W, so a lookahead for whitespace does not distinguish "safely bounded" from "mid-punctuation-run" — a punctuation tag immediately followed by more punctuation (e.g. combined con

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: per-tag-boundary-fix-notes-only-leave-notes-rgx-unbounded-as-is

WORKING DIRECTION (regex-level verified, not full pylint CLI). Fix only the literal --notes branch (which pylint fully controls via re.escape): per tag, use \b if the tag ends in a word character, else use (?!\w) (non-consuming negative lookahead) instead of \b. Leave notes_rgx completely untouched 

**Hypothesis**: The \b-boundary bug is fixable for --notes specifically (since pylint controls escaping/construction of each literal tag) without touching notes_rgx's own \b, because notes_rgx already relies on that \b for its existing TO.*DO-vs-Todoist regression test, and a free-form regex's "last character" isn't statically classifiable.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: special_case_notes_rgx_only

REFUTED. Leave the shared trailing \b in place and only special-case the notes_rgx branch.

**Hypothesis**: Hypothesized that the bug was specific to the notes_rgx config path. Refuted: self.config.notes (the built-in FIXME/XXX/TODO list, and any user-supplied custom notes list) goes through the exact same shared \b, and a user's custom notes list — not just notes_rgx — can also contain punctuation-only tags (e.g. notes=[???]). The fix must apply to the notes join itself, not just the notes_rgx branch, 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Tried: remove_boundary_entirely

REFUTED (not tested — rejected by inspection). Simply drop the trailing \b from the regex.

**Hypothesis**: Hypothesized that removing \b entirely would fix punctuation tags trivially. Refuted without needing to run it: this would immediately regress the TODOIST/FIXMENOW substring-rejection behavior already covered by tests/checkers/unittest_misc.py, which the original \b was clearly added to preserve (rejecting tag as substring of a longer identifier).

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X10 — Tried: per_tag_boundary_notes_only_keep_notes_rgx_bounded

In pylint/checkers/misc.py EncodingChecker.open(), build each literal --notes tag's boundary conditionally: append \b if the tag ends in a word char, else append (?!\w) lookahead. Splice as before into the alternation with notes_rgx (which keeps its own trailing \b unchanged, since it's user-supplie

**Hypothesis**: A single trailing \b after the whole (notes|notes_rgx) alternation can never fire right after a punctuation-only tag like '???', since both sides of that position are \W and \b requires a \w/\W transition. Making the boundary conditional per literal tag (\b for tags ending in \w, (?!\w) otherwise) fixes punctuation tags while leaving notes_rgx's own \b untouched — falsifiable if '???' still doesn'

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X11 — Tried: uniform_lookahead_boundary_notes_and_notes_rgx

In pylint/checkers/misc.py EncodingChecker.open(), replace the single trailing \b (applied once after the whole alternation) with a uniform (?!\w) negative-lookahead applied to both the literal notes group and notes_rgx, instead of branching per-tag. Simpler diff (one regex change, no per-tag condit

**Hypothesis**: Replacing \b with (?!\w) everywhere (not just for literal tags) fixes punctuation tags identically to the per-tag approach, since (?!\w) only cares about what follows, not what precedes — falsifiable by checking whether it changes matching behavior for any existing alnum-ending notes_rgx pattern relative to \b (e.g., a tag directly followed by another word char with no boundary in between).

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X12 — Sources consulted for pylint dev

- Issue pylint-dev/pylint#5859; pylint/checkers/misc.py open() (this session, base commit 182cc539b815); tests/functional/f/fixme.py, fixme.rc
- Own analysis of pylint/checkers/misc.py:119-128 plus pylint-dev/pylint#5859 issue examples using ???/!!! note tags
- Own regex experiment (tmp/research/test_regex.py), contrasted against tests/functional/f/fixme.rc's notes-rgx=FIXME(?!.*ISSUE-\d+)|TO.*DO

### X13 — What has been investigated about pylint dev

Ground already covered by research on this subject.

- **regex_fix_strategy** — What is the correct replacement for the trailing/leading (word-boundary) word-boundary assertions in the _fixme_pattern regex (misc.py open(), ~line 122-126) so that both word tags (FIXME, TODO) and a
  Looked in: pylint/checkers/misc.py open() method, regex_string construction
- **notes_rgx_interaction** — Does the same boundary bug affect the --notes-rgx option (which is spliced into the same alternation with the same trailing (word-boundary)), and should the fix apply boundary logic to notes_rgx tags 
  Looked in: pylint/checkers/misc.py open(), regex_string construction with self.config.notes_rgx
- **existing_test_impact** — Does the proposed regex fix keep tests/checkers/unittest_misc.py passing unmodified (test_xxx_without_space, test_xxx_middle, test_dont_trigger_on_todoist, test_absent_codetag, test_other_present_code
  Looked in: tests/checkers/unittest_misc.py, run via probe_run_pytest_selection
