---
name: pylint-dev-pylint-5859
description: The pylint-dev-pylint-5859 subject: fixing the W0511 fixme-tag regex trailing-\b bug for punctuation-only note tags.
subject: pylint-dev-pylint-5859
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Do not use full pylint CLI invocation in this venv/worktree |
| `R2` | Rules | Do not remove/alter notes_rgx's shared trailing \b |
| `R3` | Rules | Per-tag \b-vs-(?!\w) trick applies only to literal notes, not notes_rgx |
| `R4` | Rules | fix-discover-files-match-root-with-trailing-sep does not apply here |
| `R5` | Rules | switch-match-to-fullmatch is also a topic mismatch here |
| `X2` | References | unittest_misc.py test_xxx_middle is unaffected by \b changes |
| `X3` | References | pylint CLI does not run in this sandbox (Python 3.13 vs old pylint checkout) |
| `X4` | References | Root cause: word-boundary \b in EncodingChecker note regex, and the confirmed fix |


## Instructions

## Rules

### R1 — Do not use full pylint CLI invocation in this venv/worktree

Running `python -m pylint ... --notes="YES,???"` end-to-end in this worktree/venv fails with `UnknownMessageError: No such message id or symbol 'c-extension-no-member'` raised during Run.__init__, before the checker under test is even reached. This is an environment/message-registry mismatch unrelated to any regex/notes fix. Use CheckerTestCase-style direct checker invocation instead (as tests/checkers/unittest_misc.py already does) — that path doesn't go through Run/PyLinter's msgs_store init and works fine.

### R2 — Do not remove/alter notes_rgx's shared trailing \b

In EncodingChecker.open() (pylint/checkers/misc.py), the regex is rf"#\s*({notes}|{notes_rgx})\b" — notes_rgx is spliced in raw, sharing one trailing \b with notes. When fixing the --notes punctuation-boundary bug (tags like "???" never matching), do NOT remove/weaken this \b for the notes_rgx branch.

Why: tests/functional/f/fixme.rc sets notes-rgx=FIXME(?!.*ISSUE-\d+)|TO.*DO. fixme.py has "# Todoist API mentioned should not result in a message." which fixme.txt asserts must NOT be flagged. TO.*DO matches "Tod...do" inside "Todoist"; only the trailing \b (failing because "i" follows "do") stops it from matching. Removing \b there breaks this regression test.

### R3 — Per-tag \b-vs-(?!\w) trick applies only to literal notes, not notes_rgx

notes_rgx is a free-form user regex — its "last matched character" is not statically known, so you cannot choose \b vs (?!\w) per-alternative for it the way you can for literal --notes tags (which pylint controls via re.escape). Fix only the notes branch; leave notes_rgx's construction/boundary untouched.

### R4 — fix-discover-files-match-root-with-trailing-sep does not apply here

The approach fix-discover-files-match-root-with-trailing-sep targets pylint/lint/pylinter.py's _discover_files/ignore-paths code path (see [[discover-files#X50]] and [[pylint-discover-files-ignore-paths#X1]]), but this topic's (pylint-dev__pylint-5859) actual issue is misc.py's notes_rgx/EncodingChecker word-boundary failing on punctuation-only note tags like '???' — see [[pylint-dev-pylint-5859#X4]] for the real root cause and confirmed fix. These are unrelated code paths; reported 3x now (stages tune, tuning) as a mismatch. Same class of cross-task contamination already tracked for flask-5063 at [[pylint-discover-files-ignore-paths#X1]].

### R5 — switch-match-to-fullmatch is also a topic mismatch here

switch-match-to-fullmatch ([[discover-files#X42]]: changing ignore-paths regex matching from `re.Pattern.match` to `.fullmatch` in `_is_in_ignore_list_re`) was also reported (stages measurement, tuning) as an attempted fix for this topic's punctuation-tag bug. It cannot apply: that code path is pylinter.py's ignore-paths matching, unrelated to misc.py's `_fixme_pattern`/notes_rgx construction ([[pylint-dev-pylint-5859#X4]]), and [[discover-files#X42]] itself was already deprioritized as orthogonal even within its own (ignore-paths) topic. Same class of mismatch as R4 — check the actual failing code path (misc.py, not pylinter.py) before proposing an ignore-paths approach here.

## References

### X2 — unittest_misc.py test_xxx_middle is unaffected by \b changes

tests/checkers/unittest_misc.py:55-60 `test_xxx_middle` uses code "# midle XXX" (note: "midle" is a typo for "middle", not an actual middle-of-line placement of XXX) and expects assertNoMessages(). It passes because the checker regex requires the tag immediately after `#\s*` — matching is anchored right after the `#`, not searched anywhere in the string — so "midle" (not "XXX") at that position means the XXX alternative never matches at all, regardless of any `\b`-suffix change. This test exercises the `#\s*` prefix behavior, not boundary logic, so it's irrelevant to (and unaffected by) fixes targeting the trailing `\b`.

### X3 — pylint CLI does not run in this sandbox (Python 3.13 vs old pylint checkout)

Running the actual `pylint` CLI against this checkout fails with "Problem importing module ... Unable to find module for .../pylint/checkers/refactoring" under the sandbox's Python 3.13. This looks like an environment/packaging incompatibility unrelated to the notes_rgx bug, not something to fix as part of this task. Workaround used: verify regex behavior directly with standalone Python snippets that reconstruct the regex string exactly as open() builds it and run .search() against fixture file contents (e.g. tests/functional/f/fixme.py), comparing to the expected .txt output — this is sufficient since the whole bug lives in the regex string construction, not in checker plumbing.

### X4 — Root cause: word-boundary \b in EncodingChecker note regex, and the confirmed fix

In pylint/checkers/misc.py EncodingChecker.open() (~lines 119-128), the notes regex is built as `#\s*({notes})\b` where `notes = "|".join(re.escape(note) for note in self.config.notes)`. The trailing `\b` requires a transition between a word char and non-word char. For a punctuation-only tag like `???`, if followed by another non-word char (e.g. `:`), there's no boundary, so the regex never matches — this is the exact cause of pylint#5859 (`--notes="YES,???"` ignoring `???`). Verified: `re.compile(rf'#\s*({notes})\b').search('# ??? what')` → None.

**Confirmed fix (worked):** apply `\b` per-alternative, only when that tag ends in a word char (`re.search(r"\w$", note)`), else omit it — do not use one shared `\b` around the whole alternation. This fixes punctuation-tag matching while still rejecting substring extensions (TODOIST for TODO, FIXMENOW for FIXME) for word tags, and keeps all 10 unittest_misc.py tests passing unmodified. `notes_rgx` must NOT get this same per-tag treatment ([[pylint-dev-pylint-5859#R3]]) since it isn't a literal tag list — see research approach `per_tag_boundary` / `conditional-word-boundary`, topic pylint-dev__pylint-5859.
