# Lessons — django-django-13447

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — IndentationError when adding method

IndentationError caused by inserting the new method before the existing `_build_app_dict` definition. The leading '+' line markers from a diff were written into the source file, breaking Python's indentation and preventing module import. The fix is to place the alias after the private method with correct 4‑space indentation.

## Lessons

### L1 — I7: Skill naming and identification

**2026-08-31** — Naming and scope of this skill
