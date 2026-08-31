# Lessons — django-django-14534

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Adding email field directly caused migration conflicts

Directly adding an `email` attribute to the custom user model conflicted with existing migrations and did not resolve the authentication TypeError. Ensure any new field aligns with the model schema and migrations.

### P2 — Fallback getattr returned empty email causing token failures

Using `getattr(user, 'email', '')` as a fallback did not provide the required email value, leading to missing email in generated tokens and test failures. Ensure the fallback supplies a valid email or adjust the token generation logic.

## Lessons

### L1 — Failure of test_iterable_boundfield_select due to ignored custom widget IDs

**2026-08-29** — test_iterable_boundfield_select failed because `BoundWidget.id_for_label` always generated an ID based on name and index, ignoring custom `id` attributes provided via widget `attrs`. This caused label `for` attributes to mismatch the widget IDs, breaking accessibility and the test expecting correct ID handling.

### L2 — Failed fix of BoundWidget.id_for_label and BoundField.id_for_label

**2026-08-29** — Attempted to fix `BoundWidget.id_for_label` by adding a simple fallback, but the test `test_iterable_boundfield_select` still failed because the `attrs` dict was not consulted, and `BoundField.id_for_label` still used the old logic. The regression caused the label `for` attribute to be wrong, leading to a mismatch in expected ID (`None` vs generated).
