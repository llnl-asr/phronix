# Lessons — django-django-15388

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Diagnosis documentation pattern

**2026-08-29** — When documenting a SWE-bench task diagnosis:
- Keep rules concise (one idea per block)
- Reference specific file paths and line numbers when possible
- Note the task context (SWE-bench, issue number, branch/commit state)
- Document what was tried and the outcomes
- Separate diagnosis from implementation - diagnosis is analysis, not code

A well-structured diagnosis helps future attempts build on prior work without repeating the same analysis.
