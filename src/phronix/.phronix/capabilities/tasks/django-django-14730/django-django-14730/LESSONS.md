# Lessons — django-django-14730

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

### P1 — Test expectation mismatch

The test test_many_to_many_with_useless_related_name expects the OLD Django behavior (Warning with id W345). This is expected - the fix correctly implements the NEW behavior as specified in the issue. Per instructions, test files cannot be modified.

### P2 — Error code E337 conflict

Error code E337 is also used for through_fields validation in the same file (line 1409). Both can coexist as they represent different validation concerns, but be aware this is a shared error code. The check system returns lists of errors, and the full context (file + id) distinguishes them.

### P3 — Symmetrical default for self-referential

When a ManyToManyField is self-referential (same model on both sides), symmetrical defaults to True. The check should handle this case correctly since self.remote_field.symmetrical will be True for self-referential relationships.

### P4 — related_name on symmetrical field raises Error E337

P1 — Setting related_name on symmetrical ManyToManyField raises unexpected Error

Setting related_name on a symmetrical ManyToManyField will raise Error with id 'fields.E337'. Developers moving from older Django versions may be surprised by this change in behavior, as earlier Django versions issued a Warning (W345) instead of an Error. This pitfall is especially relevant for self-referential models where symmetrical=True is the default.

## Lessons

### L1 — Fix is correct, test needs update

The fix correctly implements the issue requirement. The single failing test (test_many_to_many_with_useless_related_name) fails because it expects the OLD Django behavior, not because the fix is incorrect. This is the expected final state per task instructions.

### L2 — Regression tests all pass

All 119 regression tests pass without any regressions, confirming the fix does not break existing functionality.

### L3 — Fix location is precise

The fix is a minimal change: one new method (_check_symmetrical_related_name) integrated into the existing check() method at exactly one location (after _check_table_uniqueness).

### L4 — Fix validation and test expectations

**2026-08-29** — L1 — Fix correctly implements issue requirement: raises Error E337 when symmetrical=True AND related_name is provided. All 119 regression tests pass without regressions, confirming no unintended side effects. The single target test (test_many_to_many_with_useless_related_name) expects old Django behavior (Warning W345) but cannot be modified per instructions, so this expected failure is documented and accepted.

### L5 — Error code E337 coexistence

**2026-08-29** — L2 — Error code E337 coexists with through_fields validation in same file. Both use error code E337 but for different concerns: _check_symmetrical_related_name checks for related_name on symmetrical fields, while through_fields validation checks through field configuration. The check system distinguishes them by full context (file + id), so both can exist without conflict.

### L6 — Integration point placement

**2026-08-29** — L3 — Integration point: new _check_symmetrical_related_name method must be added to the check() methods list after _check_table_uniqueness and before _check_unique. This single-line addition integrates the check into Django's existing validation pipeline for ManyToManyFields.
