# Lessons — django-django-16041

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — empty_permitted filtering in empty_form property

**2026-08-29** — When accessing formset.empty_form in Django formsets, always ensure empty_permitted is filtered from kwargs passed to self.form(). The empty_form property is display-only and should not include formset-level validation parameters like empty_permitted, as Django's Form constructor does not accept this argument.
