# Lessons — sphinx-doc-sphinx-8627

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Pitfalls and lessons

**2026-08-29** — - Attempting only documentation re‑organisation without code changes does not resolve the underlying Sphinx resolution error. The fix requires actual source modifications (decorator replacement and import removal).
- Assuming the issue is solely in documentation configuration leads to wasted effort; the root cause lies in the source code's use of an incorrect Jinja2 decorator and an unused import.
- Not running targeted tests early can cause unnecessary cycles; always run the specific failing Sphinx test after each code change.
