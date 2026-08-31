# Lessons — django-django-13220

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Do not compare ordered lists

Using list equality will fail when message order differs; use set comparison.

### P2 — Hash must be based on immutable data

Using the list directly in hash will raise TypeError; convert to sorted tuple.

## Lessons
