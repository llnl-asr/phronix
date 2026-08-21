---
name: pylint-fixme-notes-word-boundary
description: Research on pylint fixme notes word boundary. Covers what is the minimal, correct replacement for the trailing \b in the fixme regex (misc.py line ~124-126) that matches both word-char tags (YES, FIXME) and punctuation-only tags (???, !!) while still preventing false matches like YESTERDAY matching tag YES; does --notes-rgx combine with --notes in the same alternation, and does whatever boundary fix is chosen also need to apply when notes_rgx is user-supplied (which may itself end in punctuation); what existing tests in tests/checkers/unittest_misc.py (or similar) exercise --notes and --notes-
subject: pylint-fixme-notes-word-boundary
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | How to evaluate a change to pylint fixme notes word boundary |
| `I2` | Instructions | How to solve pylint fixme notes word boundary |
| `I3` | Instructions | Fallback approaches for pylint fixme notes word boundary |
| `I4` | Instructions | Steps to solve pylint fixme notes word boundary |
| `X1` | References | Tried: conditional-word-boundary |
| `X2` | References | Tried: lookahead-non-word-boundary |
| `X3` | References | Tried: upstream-fix-reference |
| `X4` | References | Tried: discover_files-root-only-ignore-paths-check |
| `X5` | References | Tried: backslash-escape-in-ignore-paths-regex-transformer |
| `X6` | References | Tried: skip_subtrees-prefix-collision |
| `X7` | References | Tried: patch-_discover_files-else-branch |
| `X8` | References | Tried: reproduce-via-existing-test-fixtures |
| `X9` | References | Tried: path-normalization-mismatch-candidate |
| `X10` | References | Tried: package-with-init-py-expand-modules-gap-candidate |
| `X11` | References | Tried: toml-config-loading-candidate |
| `X12` | References | Tried: windows-path-separator-candidate |
| `X13` | References | Tried: normpath-discover-files-root |
| `X14` | References | Tried: normpath-inside-is-ignored-file |
| `X15` | References | Tried: normpath-something-at-loop-entry |
| `X16` | References | Tried: per-file-ignore-paths-check-in-else-branch |
| `X17` | References | Sources consulted for pylint fixme notes word boundary |
| `X18` | References | What has been investigated about pylint fixme notes word boundary |
























## Instructions

### I1 — How to evaluate a change to pylint fixme notes word boundary

Figure of merit: **fixme_notes_match_accuracy** (max, target 1.0).

Measured by: Fraction of held-out instances where running pylint's fixme checker (MiscChecker._check_note_regex / the built --notes regex) on a snippet correctly reports W0511 exactly on lines expected to match and does not report it on lines expected not to match; computed by running pylint --disable=all --enable=W0511 --notes=&lt;tags&gt; on each instance's source and comparing the set of reported line numbe

Cases differ along: expected, note_source, position, surrounding, tag_form.

### I2 — How to solve pylint fixme notes word boundary

Try these in order, ONE at a time. Ranked by measured **fixme_notes_match_accuracy** (max, target 1.0).

Take the first, get its detail with `research_approach(key=...)`, and implement only that. Move to the next one only if it fails. Reading them all up front costs context on every task including the ones the first approach solves, which is most of them.

An approach marked **patch on file** carries `change_patch`: the exact diff that was applied and measured. `git apply` it and go straight to verifying — do not open it, and do not rebuild it by hand. That patch is the point of having researched at all.

All are *potential*: they ranked on a corpus this research authored, which is a reason to try them in this order, not evidence any is correct. One becomes *working* when a task passes with it.

1. `A1` **conditional-word-boundary** — fixme_notes_match_accuracy unmeasured, potential — In pylint/checkers/misc.py open(), replace the single f-string regex with per-note constru
2. `A2` **lookahead-non-word-boundary** — fixme_notes_match_accuracy unmeasured, potential — In pylint/checkers/misc.py open(), replace trailing \b in regex_string with a custom bound

...and 14 lower-ranked approach(es); see `research_rank`.

### I3 — Fallback approaches for pylint fixme notes word boundary

If the leading approach fails, these were also measured, ranked by the same metric.

**`A2` lookahead-non-word-boundary** — fixme_notes_match_accuracy unmeasured
  1. `grep_locate_line(...)`
  2. Design boundary replacement (judgement)
  3. `regex_replace_in_file(...)`
  4. `probe_run_pytest_selection(...)`
  5. `probe_run_pylint_check(...)`

**`A3` upstream-fix-reference** — fixme_notes_match_accuracy unmeasured
  1. `git_log_search_keyword(...)`
  2. Compare found fix to conditional-word-boundary design (judgement)
  3. `regex_replace_in_file(...)`
  4. `probe_run_pytest_selection(...)`
  5. `probe_run_pylint_check(...)`

**`A14` normpath-discover-files-root** — fixme_notes_match_accuracy unmeasured
  1. Locate _discover_files walk loop (judgement)
  2. Normalize root (judgement)
  3. Check consistent usage (judgement)
  4. Build fixture (judgement)
  5. Repro with leading-dot invocation (judgement)
  6. Run existing test suite (judgement)## Rules

### I4 — Steps to solve pylint fixme notes word boundary

The steps that solve pylint fixme notes word boundary, in order. Run them.

1. `grep_locate_line(...)` — Read misc.py open() regex construction
2. **Design per-note boundary logic** (judgement — no tool for this)
   Decide the conditional: for each note, build re.escape(note) + (r'\b' if note[-1] is a word char else '') so punctuation-only tags aren't anchored with \b but word tags still are.
3. `regex_replace_in_file(...)` — Edit misc.py to build notes per-tag
4. `probe_run_pytest_selection(...)` — Run existing fixme tests
5. `probe_run_pylint_check(...)` — Manual repro check

## References

### X1 — Tried: conditional-word-boundary

In pylint/checkers/misc.py open(), replace the single f-string regex with per-note construction: for each note, append \b only if the note's last char is a word character (re.search(r'\w$', note)), otherwise leave it unanchored (or anchor differently). Build notes as '|'.join of these per-note patte

**Hypothesis**: The trailing \b in the regex built at pylint/checkers/misc.py open() fails for tags with no \w chars (e.g. "???") because \b requires a \w/non-\w transition that never exists. Making the boundary conditional per-tag (using \b only when the tag ends in a word char, else no boundary or a different anchor) will let punctuation-only tags match. False if applying \b conditionally breaks matching for ta

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X2 — Tried: lookahead-non-word-boundary

In pylint/checkers/misc.py open(), replace trailing \b in regex_string with a custom boundary assertion, e.g. r"(\b|(?<=\W)(?=\W)|(?<=\W)$)" or simpler r"(?:\b|(?=\W|$))" appended after the notes group, so punctuation tags followed by whitespace/EOL/other punctuation still match.

**Hypothesis**: Instead of \b, use a lookahead like (?=[^\w]|$)-style boundary that doesn't require a \w character on the left side, so it works for punctuation tags too while still preventing partial-word matches for alphabetic tags. False if this causes false positives (e.g. matching inside a larger punctuation run) that break existing tests.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X3 — Tried: upstream-fix-reference

Look up the actual pylint commit fixing #5859 (via git log/blame on misc.py or web knowledge) and apply the same per-tag conditional \b logic in pylint/checkers/misc.py open(), verifying it matches conditional-word-boundary approach's mechanism.

**Hypothesis**: Pylint's actual upstream fix for this issue (PR closing #5859) likely modifies the regex to conditionally add \b per note tag, matching the conditional-word-boundary approach. Checking the real fix confirms the correct minimal patch and avoids guessing at boundary semantics. False if the upstream diff shows a materially different fix location/mechanism.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X4 — Tried: discover_files-root-only-ignore-paths-check

Confirmed as a real code-level gap but NOT an end-to-end bug: _is_ignored_file('src/gen', [], [], [re.compile(r'^src/gen/.*$')]) returns False (leak), while '^src/gen$' correctly returns True (filtered). However, verified end-to-end that `pylint --recursive=y --ignore-paths='^src/gen/.*$' src` produ

**Hypothesis**: _discover_files (pylint/lint/pylinter.py ~585-619) calls _is_ignored_file only on `root` (bare directory string from os.walk, no trailing separator), never on individual file paths. A common ignore-paths regex style written to match full file paths (e.g. '^src/gen/.*$') does not match the bare directory string 'src/gen' (no trailing segment for .* to consume), so the directory-level check silently

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X5 — Tried: backslash-escape-in-ignore-paths-regex-transformer

REFUTED as the cause of the bug. pylint/config/argument.py::_regexp_paths_csv_transfomer wraps every --ignore-paths pattern via pathlib.PureWindowsPath, which mangles regex escapes like \. into requiring a literal backslash character, so a pattern like '.*skipme\.py' fails to match 'skipme.py'. This

**Hypothesis**: Initially suspected the PureWindowsPath-based regex transformation in _regexp_paths_csv_transfomer was mangling ignore-paths patterns and causing the reported ignore failures. Refuted: switching to a backslash-free equivalent pattern reproduced the same underlying discover_files bug, showing the transformer quirk is orthogonal, not the cause.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X6 — Tried: skip_subtrees-prefix-collision

Code-level flaw confirmed unconditionally present: 'src/gen2'.startswith('src/gen') evaluates True in isolation. Could NOT get a live end-to-end false-drop within the investigation's time budget — in the constructed test directories, os.walk happened to enumerate 'gen2' before 'gen' on this filesyst

**Hypothesis**: In _discover_files, `if any(root.startswith(s) for s in skip_subtrees): continue` is a plain string-prefix check with no path-separator boundary. If skip_subtrees contains 'src/gen' (added because that dir was ignored) and os.walk later yields sibling directory 'src/gen2', then 'src/gen2'.startswith('src/gen') is True, so gen2's files are wrongly skipped even though gen2 matches no ignore rule — a

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X7 — Tried: patch-_discover_files-else-branch

In pylint/lint/pylinter.py::_discover_files, the `else` branch (no __init__.py directory) yields raw .py files via os.path.join(root, file) without ever calling _is_ignored_file on the individual filepath — only the directory root gets checked. Fix: call _is_ignored_file(filepath, ...) per file befo

**Hypothesis**: Hypothesis: _discover_files' else-branch is the sole cause of --ignore-paths not applying under --recursive=y. Refuted by: live testing showed expand_modules() downstream already filters plain files the same way, so the simple no-__init__.py repro is unaffected by this patch either way (exit 0 on both baseline and patched).

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X8 — Tried: reproduce-via-existing-test-fixtures

Tried to reproduce the reported --ignore-paths/--recursive bug using the existing tests/regrtest_data/directory fixture and the 3 relevant tests (test_ignore_recursive, test_ignore_pattern_recursive, test_ignore_path_recursive). REFUTED as a repro: all 3 pass on the current unfixed checkout (`pytest

**Hypothesis**: Hypothesis: existing test_self.py recursive+ignore tests already reproduce the reported bug (so the fix should just make them fail then pass). Refuted by: running them against the unfixed checkout — all pass already, meaning they don't exercise the failure mode at all.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X9 — Tried: path-normalization-mismatch-candidate

Candidate root cause (untested, flagged for follow-up): the anchored ignore-paths regex (e.g. ^src/gen/.*$) is built against the user's relative invocation path ("src/"), but expand_modules.py normalizes filepath via os.path.normpath and modutils.get_module_files may yield subfilepaths that are abso

**Hypothesis**: Hypothesis: path normalization/absolutization between _discover_files, expand_modules, and modutils.get_module_files causes anchored relative ignore-paths regexes to silently stop matching for some code paths (e.g. package dirs with __init__.py, recursed via get_module_files). Would be shown false if tracing actual filepath strings passed to _is_ignored_file at each stage shows they remain consist

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X10 — Tried: package-with-init-py-expand-modules-gap-candidate

Candidate root cause (untested, flagged for follow-up): when the target directory DOES have __init__.py (a real package, e.g. gen/ as an actual package rather than plain scripts), _discover_files yields the directory root itself rather than individual files, and expand_modules() then recurses into i

**Hypothesis**: Hypothesis: the package-with-__init__.py recursion path in expand_modules.py (via modutils.get_module_files) fails to correctly apply --ignore-paths to files inside the package, unlike the plain-files path which was shown to already work via expand_modules's top-level check. Would be refuted if a live repro with an __init__.py-containing gen/ package and --ignore-paths=^src/gen/.*$ still correctly

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X11 — Tried: toml-config-loading-candidate

Candidate root cause (untested, out of scope for this aspect, flagged for whoever covers config loading): the reporter's ignore-paths config was set in pyproject.toml under [tool.pylint.MASTER], not passed on the CLI. Possible the bug is in TOML config-file loading/normalization of ignore-paths (e.g

**Hypothesis**: Hypothesis: ignore-paths values loaded from pyproject.toml's [tool.pylint.MASTER] section are not normalized/compiled into the same regex form as CLI-provided values, causing the configured pattern to silently fail to match. Would be refuted by confirming pylint/config/'s TOML loader routes ignore-paths through the same _regexp_paths_csv_transfomer as CLI parsing.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X12 — Tried: windows-path-separator-candidate

Candidate root cause (untested, low-confidence, flagged for follow-up): reporter was on Windows (paths like src\gen\about.py). _regexp_paths_csv_transfomer builds a combined regex trying both a backslash-escaped Windows form and a posix form of the PATTERN, but this was not verified against actual b

**Hypothesis**: Hypothesis: on Windows, backslash-separated file paths from os.walk/os.path.join fail to match the ignore-paths regex despite _regexp_paths_csv_transfomer's dual-form pattern construction. Would be refuted by testing on/simulating Windows path strings against the compiled regex and confirming a match.

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X13 — Tried: normpath-discover-files-root

In pylint/lint/pylinter.py:_discover_files, normalize `root` (e.g. `root = os.path.normpath(root)`) immediately inside the `for root, _, files in os.walk(something):` loop, before it is used in the skip_subtrees check, the _is_ignored_file(root, ...) check, and the yielded file paths, so ignore-path

**Hypothesis**: os.walk(something) preserves whatever path-prefix the caller passed in `something` (e.g. a leading "./"), so when pylint is invoked as `pylint --recursive=y ./src` or `pylint --recursive=y .`, os.walk yields root strings like "./src/gen" instead of "src/gen". The anchored ignore-paths regex "^src/gen/.*$" never matches this prefixed string, so the directory is never added to skip_subtrees and its 

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X14 — Tried: normpath-inside-is-ignored-file

In pylint/lint/expand_modules.py:_is_ignored_file, compute `norm_element = os.path.normpath(element)` and pass that (instead of raw `element`) to `_is_in_ignore_list_re(..., ignore_list_paths_re)`, fixing path-prefix mismatches for every caller of this shared helper (both _discover_files and expand_

**Hypothesis**: Rather than fixing the walk root in _discover_files, normalize the path centrally inside _is_ignored_file (pylint/lint/expand_modules.py), which is the single shared choke point called both from _discover_files (per-directory root) and expand_modules (per-file/module). Adding `norm_element = os.path.normpath(element)` and matching ignore_list_paths_re against norm_element instead of the raw elemen

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X15 — Tried: normpath-something-at-loop-entry

In pylint/lint/pylinter.py:_discover_files, at the top of `for something in files_or_modules:` add `if os.path.exists(something): something = os.path.normpath(something)` before the os.path.isdir/isfile check, so the os.walk(something) call itself starts from a clean path and every root it yields is

**Hypothesis**: Normalize the top-level `something` argument once, right when _discover_files starts iterating `files_or_modules`, before it's used for os.path.isdir/isfile checks or passed into os.walk. Since os.walk propagates whatever prefix its root argument had into every yielded root, normalizing the seed path once (`something = os.path.normpath(something)`) is sufficient to keep every subsequent root clean

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X16 — Tried: per-file-ignore-paths-check-in-else-branch

In PyLinter._discover_files, when walking a directory that has no __init__.py, filter each yielded .py file through _is_ignored_file(ignore, ignore_patterns, ignore_paths) in addition to the existing root-level check, so ignore-paths matches individual file paths (e.g. 'src/gen/about.py') rather tha

**Hypothesis**: The bug is that _is_ignored_file is only called against os.walk 'root' directory strings (e.g. 'src/gen', no trailing separator), which fails to match ignore-paths regexes anchored with '/.*$'; files under such directories are never individually tested against ignore rules. Fix: test each candidate file path too. Falsified if ignored files still get linted, or if legitimately non-ignored files get

**Status**: potential (no trials recorded yet). Investigated already — extend this rather than re-deriving it.

### X17 — Sources consulted for pylint fixme notes word boundary

- Issue report: user's config was in pyproject.toml [tool.pylint.MASTER]; pylint/config/ TOML parsing (not examined)
- Manual code trace of pylint/lint/pylinter.py:_discover_files and pylint/lint/expand_modules.py:_is_ignored_file/_is_in_ignore_list_re; direct repro via python REPL calls; end-to-end CLI repro with --r
- Manual code trace of pylint/lint/pylinter.py:_discover_files skip_subtrees check; direct repro of the string-prefix collision via Python REPL
- issue.md (pylint-dev/pylint#7080): --recursive=y ignores ignore-paths
- issue.md + pylint/checkers/misc.py lines 119-128
- issue.md + regex semantics of \b
- pylint GitHub issue #5859 / PR history
- pylint/config/ _regexp_paths_csv_transfomer; issue reporter's OS (Windows), paths like src\gen\about.py

### X18 — What has been investigated about pylint fixme notes word boundary

Ground already covered by research on this subject.

- **regex_boundary_fix** — What is the minimal, correct replacement for the trailing \b in the fixme regex (misc.py line ~124-126) that matches both word-char tags (YES, FIXME) and punctuation-only tags (???, !!) while still pr
  Looked in: pylint/checkers/misc.py around _fixme_pattern construction (regex_string = rf"#\s*({notes})\b")
- **notes_rgx_interaction** — Does --notes-rgx combine with --notes in the same alternation, and does whatever boundary fix is chosen also need to apply when notes_rgx is user-supplied (which may itself end in punctuation)?
  Looked in: pylint/checkers/misc.py open_paren, the notes_rgx branch of the regex_string construction
- **existing_test_coverage** — What existing tests in tests/checkers/unittest_misc.py (or similar) exercise --notes and --notes-rgx, and what pattern do they use for asserting match/no-match, so the fix can be validated the same wa
  Looked in: tests/checkers/unittest_misc.py or tests/functional related to fixme/W0511
- **regression_risk_substring_matches** — Does the chosen fix preserve the existing behavior that a tag must not match as a mere substring of a larger word (e.g. 'YES' not matching inside 'YESTERDAY'), by using a boundary condition that still

...and 1 more line(s) of ground covered.
