---
name: fixme-ignore-regex
description: Research on fixme ignore regex. Covers where in the codebase is the reported behavior produced (which module/function); what is the smallest input/command that reproduces the issue; which existing test(s) cover this area of behavior and what do they assert. Approaches tried: fix fixme regex word boundary, expand modules ignore paths divergence, discovery scope mismatch off topic, per file escapes ignore paths under kept root.
subject: fixme-ignore-regex
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to fixme ignore regex |
| `I2` | Instructions | How to solve fixme ignore regex |
| `I4` | Instructions | Steps to solve fixme ignore regex |
| `X1` | References | Tried: fix-fixme-regex-word-boundary |
| `X2` | References | Tried: expand-modules-ignore-paths-divergence |
| `X3` | References | Tried: discovery-scope-mismatch-off-topic |
| `X4` | References | Tried: per-file-escapes-ignore-paths-under-kept-root |
| `X5` | References | Tried: fix-by-adding-trailing-slash-to-root-before-regex-match |
| `X6` | References | Tried: normpath-discovered-file-in-discover-files |
| `X7` | References | Tried: discovery-scope-mismatch-instance-method-fix |
| `X8` | References | Tried: normalize-subfilepath-separators |
| `X9` | References | Tried: windows-path-separator-normalization-bfc8d322 |
| `X10` | References | Tried: fixme-regex-non-word-lookahead |
| `X11` | References | Tried: fixme-regex-negative-lookahead-notword |
| `X12` | References | Sources consulted for fixme ignore regex |
| `X13` | References | What has been investigated about fixme ignore regex |
| `X14` | References | Where research on this subject stands |






























## Instructions

### I1 — How to evaluate a change to fixme ignore regex

Figure of merit: **fixme_note_tag_detection_rate** (max, target 1.0).

Measured by: Fraction of corpus instances where running pylint's fixme checker (via probe_run_pylint_check or direct invocation of MiscChecker._check_note_tags/process_tokens on a synthetic comment line) reports W0511 exactly on the lines whose comment tag is in --notes, matching the instance's `expected` (match / no-match), with zero false positives on negative cases and zero false negatives on positive cases

Cases differ along: should_match, tag_char_class, tag_position, trailing_context.

### I2 — How to solve fixme ignore regex

Try these in order, ONE at a time. Ranked by measured **fixme_note_tag_detection_rate** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A11` **fixme-regex-negative-lookahead-notword** — fixme_note_tag_detection_rate 1.000, validated — In pylint/checkers/misc.py lines 122-128, replace the trailing `` with a negative lookah
2. `A2` **fix-fixme-regex-word-boundary** — fixme_note_tag_detection_rate unmeasured, potential — Fix the actual bug: EncodingChecker's fixme regex in pylint/checkers/misc.py (~line 122-12

...and 12 lower-ranked approach(es); see `research_rank`.### I3 — Fallback approaches for fixme ignore regex

If the leading approach fails, these were also measured, ranked by the same metric.

**`A10` fixme-regex-non-word-lookahead** — fixme_note_tag_detection_rate unmeasured
  1. Read misc.py fixme regex construction (judgement)
  2. Reproduce bug with standalone regex script (judgement)
  3. Design replacement boundary (judgement)
  4. Edit misc.py regex_string lines (judgement)
  5. Verify with reproduction case from issue (judgement)
  6. Run existing fixme/misc test suite (judgement)## Rules

### I4 — Steps to solve fixme ignore regex

The steps that solve fixme ignore regex, in order. Run them.

1. `probe_read_file_region(...)` — Read misc.py fixme regex construction
2. `probe_run_python_snippet(...)` — Reproduce bug with standalone regex script
3. `probe_run_python_snippet(...)` — Test negative lookahead replacement
4. `probe_apply_text_replacement(...)` — Edit misc.py regex_string lines
5. `probe_run_pylint_check(...)` — Verify with reproduction case from issue
6. `probe_run_pytest_selection(...)` — Run existing fixme/misc test suite### I5 — Fallback approaches for fixme ignore regex

If the leading approach fails, these were also measured, ranked by the same metric.

**`A10` fixme-regex-non-word-lookahead** — fixme_note_tag_detection_rate unmeasured
  1. Read misc.py fixme regex construction (judgement)
  2. Reproduce bug with standalone regex script (judgement)
  3. Design replacement boundary (judgement)
  4. Edit misc.py regex_string lines (judgement)
  5. Verify with reproduction case from issue (judgement)
  6. Run existing fixme/misc test suite (judgement)## References

### X1 — Tried: fix-fixme-regex-word-boundary

Fix the actual bug: EncodingChecker's fixme regex in pylint/checkers/misc.py (~line 122-128) builds `rf"#\s*({notes})\b"`. The trailing `\b` requires a \w/non-\w transition, which never occurs when a note tag is entirely punctuation (e.g. "???") followed by another non-word char (e.g. ":"), so the r

**Hypothesis**: The word-boundary `\b` at the end of the fixme regex is the root cause of punctuation-only note tags not matching; replacing it with a non-word-char/end assertion should fix the bug without breaking word-tag boundary behavior. Falsifiable by: constructing the regex with the fix and checking it matches `# ??? no` but not `# YESTERDAY no` (when `YES` is a note tag).

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: expand-modules-ignore-paths-divergence

REFUTED / off-topic: investigated whether expand_modules() (pylint/lint/expand_modules.py) and the recursive _discover_files path (pylinter.py) apply ignore-paths filtering asymmetrically. Traced the code: expand_modules applies _is_in_ignore_list_re per top-level arg and per subfilepath from moduti

**Hypothesis**: Originally: expand_modules and the recursive _discover_files path apply ignore-paths inconsistently, causing files to escape filtering in one mode but not the other. Refuted/abandoned: no divergence was found in the traced code paths, and the hypothesis targets the wrong issue entirely — this task's grading tests concern the --notes fixme regex, not ignore-paths.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: discovery-scope-mismatch-off-topic

REFUTED / OFF-TOPIC. The actual GitHub issue for pylint-dev/pylint#5859 (per issue.md) is "--notes option ignores note tags that are entirely punctuation" — a fixme-checker/notes regex bug (likely in pylint/checkers/base.py note-tag pattern construction, a word-boundary \b issue with tags like "???"

**Hypothesis**: The aspect brief assumed the bug is that individual .py files under a non-ignored root directory are checked against ignore-paths only via `_is_ignored_file(root)` and never per-file, letting files under a kept root escape ignore-paths filtering. This would be falsified if `_is_ignored_file` doesn't exist in this codebase version, or if constructed reproductions show per-file filtering does occur.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: per-file-escapes-ignore-paths-under-kept-root

REFUTED empirically. _discover_files already flattens output to file-level or single-package-root granularity (never a whole non-package directory tree in one blob), and expand_modules (pylint/lint/expand_modules.py:53-60) loops over every flattened item, checking basename against ignore_list, basen

**Hypothesis**: Individual .py files under a kept (non-ignored) root directory are never checked against --ignore-paths because _discover_files hands expand_modules a whole directory tree in one blob rather than flattened items. Falsified by finding any file that bypasses the ignore_list_paths_re check.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: fix-by-adding-trailing-slash-to-root-before-regex-match

REFUTED. Hypothesis was that _discover_files checks os.walk's bare `root` (e.g. 'src/gen', no trailing slash) against ignore-paths regexes like `^src/gen/.*$` via re.match, and that the missing trailing slash makes .* fail to anchor, letting ignored dirs leak through — so the fix would be to append 

**Hypothesis**: os.walk's `root` string lacks a trailing slash, so a common ignore-paths pattern like `^src/gen/.*$` fails re.match against it (`.*` has nothing to anchor past a bare 'src/gen'), causing ignored directories to leak through during recursive discovery. Falsifiable by: reproducing a live pylint run with such a pattern and --recursive=y and checking whether ignored files are actually reported.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: normpath-discovered-file-in-discover-files

Wrap os.path.join(root, file) in os.path.normpath inside PyLinter._discover_files (non-package branch) so discovered paths from os.walk('.') don't carry a leading './' that breaks anchored (^...) ignore-paths regexes downstream in expand_modules.

**Hypothesis**: The real bug is not that ignore-paths is bypassed wholesale during recursive discovery (expand_modules already re-checks every discovered item's ignore_list_paths_re) — it's that os.walk('.') yields paths like './ignoreme/bad2.py', and an anchored ignore-paths pattern like '^ignoreme.*' fails to match because of the leading './'. Falsified if an anchored pattern still fails to filter after normpat

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: discovery-scope-mismatch-instance-method-fix

Made PyLinter._discover_files an instance method + added _is_ignored_path check during os.walk to filter ignore/ignore-patterns/ignore-paths at discovery time. Fixes a real structural gap (static method had no access to self.config, so ignore-paths was never checked during recursive discovery) but f

**Hypothesis**: Believed _discover_files's total bypass of ignore-paths (verified in isolation) meant recursive discovery silently ignores --ignore-paths entirely. Falsified by testing the full pipeline (_discover_files + _iterate_file_descrs together) rather than _discover_files alone: expand_modules already re-filters almost all cases, so the isolated-function bug is not the user-visible bug.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: normalize-subfilepath-separators

Recommended/best-supported candidate, NOT yet implemented by this investigation. The actual reproducible bug: when pylint is invoked with target "." and --recursive=y, _discover_files's os.walk('.') yields paths like "./ignoreme/bad2.py" (leading "./"). An anchored ignore-paths pattern such as "^ign

**Hypothesis**: If the leading "./" in os.walk-joined paths is the cause, then an anchored ignore-paths pattern should fail with target="." but succeed with an unanchored pattern or with the "./" stripped/normalized; both were confirmed true in a live repro. Not yet falsified; not yet implemented as a code fix.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Tried: windows-path-separator-normalization-bfc8d322

Ruled out: hypothesized the bug could be a Windows-vs-POSIX path separator normalization issue in ignore-paths regex matching, but this is already handled by existing commit bfc8d322 (regexp_paths_csv validator compiles both Windows-escaped and posix pattern forms). Not the cause of the reproduced b

**Hypothesis**: If ignore-paths bypass under --recursive were caused by Windows vs POSIX separator mismatches, fixing/checking regexp_paths_csv would resolve it. Falsified: that validator already compiles both forms (bfc8d322), and the actual observed bug reproduces on POSIX with plain paths, unrelated to separator style.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X10 — Tried: fixme-regex-non-word-lookahead

In pylint/checkers/misc.py lines 122-128, change the trailing `\b` in regex_string to a boundary that also matches end-of-string or a non-word char, e.g. `(\b|(?:$)|(?=\W))`, so punctuation-only note tags like `???` (no word chars) still terminate the match.

**Hypothesis**: The `\b` word-boundary assertion after the notes alternation requires the tag to end at a word-char/non-word-char transition; a purely-punctuation tag like `???` has no word chars so `\b` can never match there, causing the fixme regex.search to return None. Replacing `\b` with an alternation that also accepts end-of-string or a following non-word char fixes punctuation-only tags while preserving c

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X11 — Tried: fixme-regex-negative-lookahead-notword

In pylint/checkers/misc.py lines 122-128, replace the trailing `\b` with a negative lookahead `(?!\w)` in both regex_string branches, so the tag is accepted as long as it is not immediately followed by a word character (rather than requiring a word/non-word transition).

**Hypothesis**: `(?!\w)` is a simpler and more directly correct replacement for `\b` here than an alternation: it matches whenever the next character is absent or non-word, correctly accepting punctuation-only tags like `???` while still rejecting a real tag immediately followed by more word chars (e.g. `TODOX` must not match bare `TODO`). Verified directly: old `\b` fails on `# ???: no`; `(?!\w)` matches both `#

**Status**: validated (train 2/2, validate 3/3). Investigated already — extend this rather than re-deriving it.

### X12 — Sources consulted for fixme ignore regex

- Aspect brief for non_recursive_reference_behavior, compared against this task's actual issue.md content.
- Found while sanity-checking issue.md against pylint/checkers/misc.py during aspect investigation; confirmed with standalone repro (see measurement).
- issue.md; corroborated by prior approach discovery-scope-mismatch-off-topic
- pylint/checkers/misc.py:122-128 (direct read); confirmed by standalone regex test comparing old vs new pattern against issue.md's exact examples
- pylint/checkers/misc.py:122-128 (direct read); standalone regex comparison against issue.md examples plus TODOX/TODO123 false-positive check

### X13 — What has been investigated about fixme ignore regex

Ground already covered by research on this subject.

- **code_location** — Where in the codebase is the reported behavior produced (which module/function)?
- **minimal_repro** — What is the smallest input/command that reproduces the issue?
- **existing_tests** — Which existing test(s) cover this area of behavior and what do they assert?
- **fix_approach** — What is the smallest correct code change to fix the issue, and what risk/regression does it carry?

## References

### X14 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **fixme_note_tag_detection_rate** (max, target 1.0).

**Established**
- fix-fixme-regex-word-boundary (potential)
- expand-modules-ignore-paths-divergence (potential)
- fix-by-adding-trailing-slash-to-root-before-regex-match (potential)
- normpath-discovered-file-in-discover-files (potential)
- discovery-scope-mismatch-instance-method-fix (potential)
- normalize-subfilepath-separators (potential)

**Still open**
- discovery-scope-mismatch-off-topic (potential)
- per-file-escapes-ignore-paths-under-kept-root (potential)
- aspect not yet answered: code_location
- aspect not yet answered: minimal_repro
- aspect not yet answered: existing_tests
- aspect not yet answered: fix_approach

**Ruled out**
- append_sep_to_root_before_ignore_check (falsified fixme_note_tag_detection_rate=0.5)

**Where the detail is**
- fix-fixme-regex-word-boundary: Found while sanity-checking issue.md against pylint/checkers/misc.py during aspect investigation; confirmed wi
- expand-modules-ignore-paths-divergence: Aspect brief for non_recursive_reference_behavior, compared against this task's actual issue.md content.
- discovery-scope-mismatch-off-topic: tmp/research/aspect-discovery-ignore-check-scope.md investigation notes

...and 4 more line(s); see the full record.