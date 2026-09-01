# Lessons — matplotlib-matplotlib-18869

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Missing helper _parse_to_version_info

Tests expect `matplotlib._parse_to_version_info`. If this helper is not implemented, the target tests will raise `AttributeError`. Ensure either to implement the helper or adjust tests accordingly.

## Lessons
