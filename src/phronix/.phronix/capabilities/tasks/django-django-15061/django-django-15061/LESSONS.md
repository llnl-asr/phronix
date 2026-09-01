# Lessons — django-django-15061

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — After removing the id_for_label method from MultiWidget class (5 lines

**2026-08-29** — After removing the id_for_label method from MultiWidget class (5 lines removed from django/forms/widgets.py:851-854), 3 target tests failed:

1. test_form_as_table (forms_tests.field_tests.test_multivaluefield.MultiValueFieldTest) - expects <label for="id_field1"> but gets <label> without for attribute
2. test_form_as_table (forms_tests.field_tests.test_splitdatetimefield.SplitDateTimeFieldTest) - same issue with datetime labels
3. test_form_as_table_data (forms_tests.field_tests.test_multivaluefield.MultiValueFieldTest) - same issue with field labels

The failures occur because the tests expect the `for` attribute on `<label>` tags to match input id patterns like `id_name_0`. After removing the id_for_label method, MultiWidget inherits the base Widget.id_for_label which simply returns the id unchanged (without _0 suffix), so the `for` attribute is no longer automatically generated from the widget id for MultiWidget instances.

This is the intended behavior change per the task - users should control whether they want an index in their label IDs, rather than having `_0` automatically appended. However, the 3 target tests that were written expecting the old behavior now fail.

14 regression tests continue passing, indicating no broader breakage from this change.

The fix is correct per the issue requirements (remove the method that appends _0 to ids), but there is a trade-off: the `for` attribute on labels is no longer automatically populated for MultiWidget instances, which may require users to manually set the `for` attribute on their `<label>` tags if they need label-input association.
