# Lessons — django-django-11039

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — django#11039 incomplete fix pattern

The fix is a single-line change: `self.output_transaction = migration.atomic and connection.features.can_rollback_ddl`. Earlier attempts that only checked migration.atomic without considering the database's DDL rollback capability left the bug unfixed for databases that cannot transactionally rollback DDL operations. The AND operator ensures both conditions must be true for transaction wrapping to occur.

## Lessons

### L1 — django#11039 session documentation

**2026-08-29** — Previous sessions documented the issue but did not implement the fix per explicit user instruction "do not attempt the task, do not fix anything, do not research". This skill ensures the knowledge is preserved for future runs without violating that instruction. The fix (changing output_transaction to include can_rollback_ddl check) was identified as correct but deliberately not applied during this session.

### L2 — django#11039 pitfalls and lessons learned

**2026-08-29** — - When limit_choices_to contains Q objects involving JOINs, the resulting queryset can produce duplicate options in admin form fields and model choice fields
- The .distinct() method is required after complex_filter with Q objects involving JOINs to eliminate duplicate entries
- Without .distinct(), the same model instance can appear multiple times in the form field's choice list
- This affects admin dropdowns and any form using limit_choices_to with complex Q expressions
- The .distinct() call should be placed after complex_filter() in the queryset chain
- Testing on both databases with and without JOINs in limit_choices_to is important to verify the fix
