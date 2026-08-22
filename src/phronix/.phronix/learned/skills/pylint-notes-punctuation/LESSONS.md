# Lessons — pylint-notes-punctuation

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pylint --notes ignores tags that are only punctuation

When using pylint's --notes option, any note tag that consists solely of punctuation characters (e.g., "???") is ignored and does not trigger a fixme warning (W0511). Ensure note tags contain at least one alphanumeric character to be recognized.

## Lessons

### L1 — Remove trailing word boundary from notes regex to recognize punctuation-only tags

**2026-08-21** — Root cause: the regex used in `pylint/checkers/misc.py` includes a trailing ``\b`` word‑boundary, which only matches when the note tag ends with an alphanumeric character. Punctuation‑only tags (e.g. ``???``) lack such a character, so they are not matched and no ``W0511`` warning is emitted.\n\nFix: modify the regex construction to omit the trailing ``\b``. Replace:\n```python\nif self.config.notes_rgx:\n    regex_string = rf"#\s*({notes}|{self.config.notes_rgx})\b"\nelse:\n    regex_string = rf"#\s*({notes})\b"\n```\nwith:\n```python\nif self.config.notes_rgx:\n    regex_string = rf"#\s*({notes}|{self.config.notes_rgx})"\nelse:\n    regex_string = rf"#\s*({notes})"\n```\n\nAfter this change, ``pylint --notes="YES,???"`` correctly reports a fixme warning for both ``YES`` and ``???`` tags.\n\nWhy: removing the word‑boundary allows the regex to match any sequence of characters after ``#`` and optional whitespace, including pure punctuation, satisfying the ``--notes`` filter logic.\n\nReference: see ``pylint/checkers/misc.py`` where the regex is built.\n","description":"Root cause and fix for punctuation‑only note tags being ignored by pylint's --notes option.","layer":"project"}<|end|><|start|>assistant<|channel|>analysis<|message|>We called skill_write_lesson, but we need to see if it succeeded.<|end|><|start|>assistant<|channel|>commentary to=functions.phronix_skill_write_lesson<|message|>{
