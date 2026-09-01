# Lessons — django-django-13590-resolve-lookup-value

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Attempt applied * unpacking to ALL tuples/lists in resolve_lookup_valu

**2026-08-29** — Attempt applied * unpacking to ALL tuples/lists in resolve_lookup_value, which:
- Fixed the named tuple case (test_range_lookup_namedtuple passed)
- Broke 5 regression tests because * unpacking tried to iterate over CombinedExpression objects (TypeError: 'CombinedExpression' object is not iterable and TypeError: list() takes at most 1 argument (2 given))

The 5 broken tests were:
1. test_complex_expressions_do_not_introduce_sql_injection_via_untrusted_string_inclusion
2. test_expressions_in_lookups_join_choice
3. test_in_lookup_allows_F_expressions_and_expressions_for_datetimes
4. test_in_lookup_allows_F_expressions_and_expressions_for_integers
5. test_range_lookup_allows_F_expressions_and_expressions_for_integers

Root cause: blanket * application is too aggressive - must only apply * for named tuples (detected by hasattr(type(value), '_fields')), not for regular tuples/lists or expression objects.
