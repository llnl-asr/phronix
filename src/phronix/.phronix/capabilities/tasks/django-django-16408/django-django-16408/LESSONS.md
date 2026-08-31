# Lessons — django-django-16408

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Changing the wrong select_related target

Selecting `'tournament_pool'` leads to a mismatched `PoolStyle` object; ensure you select `'pool'` instead.

### P2 — Leaving the diff empty

An empty diff means no change was applied; verify the file was actually modified.

## Lessons
