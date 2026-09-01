# Lessons — django-django-12497-hint-correction

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — django-12497 hint correction lesson

**2026-08-29** — When correcting the ambiguous relationship hint in django/db/models/fields/related.py, simply swapping ForeignKey to ManyToManyField in the error text (lines 1312 and 1332) was directionally correct but insufficient. The previous attempt (0 of 2 target tests) changed ForeignKey→ManyToManyField but kept symmetrical=False in the hint. However, the test expectations still reference the old ForeignKey pattern, and the complete hint should also note that symmetrical is Django 3.0+ optional for recursive relationships. A full correct fix: (1) confirm the ManyToManyField change is proper, (2) remove or qualify the symmetrical=False requirement since it's Django 3.0+ optional for recursive M2M, and (3) ensure the through parameter guidance is architecturally sound. The attempt's core change (ForeignKey → ManyToManyField) is correct but needs the full context of the many-to-many parameter semantics to pass evaluation.
