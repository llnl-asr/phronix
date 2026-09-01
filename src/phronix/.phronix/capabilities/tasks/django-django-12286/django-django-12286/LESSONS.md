# Lessons — django-django-12286

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — When fixing language code consistency checks, always verify edge cases

**2026-08-29** — When fixing language code consistency checks, always verify edge cases: codes without dashes, codes with multiple dashes, and `@`-based locale formats. The `split('-')[0]` pattern is correct for Django's language fallback but must only apply when exact match fails. Test all scenarios explicitly: de-at with de available (should pass), de-at with only en (should raise E004), fr with only en (should raise E004 — regression guard), and exact matches (should always pass).
