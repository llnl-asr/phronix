# Lessons — pylint-dev-pylint-5859

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Removed word‑boundary caused false positives

Simply dropping the `\b` makes the regex match any comment containing the notes string, leading to extra fixme warnings for unrelated comments (e.g., Todoist API messages).

### P2 — Removed word‑boundary caused false positives

Removed word‑boundary caused false positives: Simply dropping the \b makes the regex match any comment containing the notes string, leading to extra fixme warnings for unrelated comments (e.g., Todoist API messages).

## Lessons

### L1 — Removal of word‑boundary caused false positive fixme warnings

**2026-08-29** — The attempt removed the word‑boundary (`\b`) from the regex in `pylint/checkers/misc.py`, causing the `EncodingChecker` to trigger on normal comments such as `# Todoist API: ...`. This broke the test `TestFixme.test_dont_trigger_on_todoist`, which expected no `fixme` messages. The fix re‑adds the word‑boundary and adds an alternative to match punctuation‑only notes, preventing false positives while still handling the original bug.
