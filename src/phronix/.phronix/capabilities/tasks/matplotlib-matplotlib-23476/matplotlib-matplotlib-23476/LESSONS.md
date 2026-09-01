# Lessons — matplotlib-matplotlib-23476

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Adding the DPI guard alone is insufficient

The patch restores dpi but the figure loses its canvas attribute, causing AttributeError in set_size_inches. Future fixes must also recreate the canvas/manager.

## Lessons
