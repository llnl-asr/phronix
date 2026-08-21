# Lessons — pylint-fixme-checker

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — --notes tags of pure punctuation (e.g. "???") not detected by fixme checker

**2026-08-21** — Symptom: `pylint --notes="YES,???"` reports W0511 for `# YES: ...` but not `# ???: ...`.

Root cause: in pylint/checkers/misc.py `_fixme_pattern` construction, the regex used `\b` (word boundary) after the note-tag group: `rf"#\s*({notes})\b"`. `\b` only matches between a word char and non-word char, so it never matches after a tag made entirely of punctuation (no word chars at all) — the boundary condition is never satisfied.

Fix: replace `\b` with a lookahead that accepts `:`, whitespace, or end-of-string: `rf"#\s*({notes})(?=(:|\s|\Z))"`. Apply to both branches (with and without `self.config.notes_rgx`). This is a targeted regex fix, verified against tests/checkers/unittest_misc.py::TestFixme (all 11 tests pass, including the new non_alphanumeric_codetag case).
