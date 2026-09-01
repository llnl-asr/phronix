# Lessons — django-django-13158

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Returning [] for all cases breaks non‑union handling

**2026-08-29** — Attempt 1 replaced `self.queryset.none()` with `[]` unconditionally. This caused the form to add no objects for regular querysets, breaking existing behavior. The fix must detect union querysets before returning `[]`.
