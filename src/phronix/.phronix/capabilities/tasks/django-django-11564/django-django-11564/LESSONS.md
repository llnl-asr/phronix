# Lessons — django-django-11564

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — SCRIPT_NAME support addition attempt failed

**2026-08-29** — Attempt to add SCRIPT_NAME support in STATIC_URL and MEDIA_URL failed because the agent produced no patch and no implementation changes. The approach of modifying the static tag render method and FileSystemStorage did not result in any code modifications.
