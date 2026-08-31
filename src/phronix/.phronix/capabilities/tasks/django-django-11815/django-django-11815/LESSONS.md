# Lessons — django-django-11815

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — P1

The test_serialize_enums test expects the old value-based format (TextEnum('A')) but the fix produces name-based format (TextEnum['A']). This failure actually confirms the fix works per the issue requirements.

### P2 — P2

The test_serialize_class_based_validators test may reflect a pre-existing issue or cascading effect unrelated to the enum fix. Do not assume it indicates a broken fix.

### P3 — P3

Re-applying the same value → name change without noting three prior attempts wastes an attempt. Always check the record first.

### P4 — P4

Do not chase failing tests as if they indicate a broken fix — they may reflect the intentionally changed behavior the issue requires.

### P5 — P5

Do not modify test files even when tests appear to assert incorrect (old) behavior.

## Lessons
