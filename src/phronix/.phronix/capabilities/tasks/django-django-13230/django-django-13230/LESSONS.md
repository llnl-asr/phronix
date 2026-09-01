# Lessons — django-django-13230

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Adding comments alone insufficient

**2026-08-29** — Simply adding `comments=getattr(item, 'comments', None)` does not generate the `<comments>` element in the RSS2 feed because the template rendering does not include it. Further work is needed to ensure the feed includes the element when present.
