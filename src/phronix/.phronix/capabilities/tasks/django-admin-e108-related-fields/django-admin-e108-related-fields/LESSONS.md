# Lessons — django-admin-e108-related-fields

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — Django admin E108 check for related fields in list_display

**2026-08-29** — 4. Pitfalls and lessons: Modifying _get_non_gfk_field to raise FieldDoesNotExist for GenericForeignKey did not resolve the issue — check passed but runtime still failed. The discrepancy between check validation and label_for_field runtime resolution is the root cause. Generalizing to GenericForeignKey was insufficient for regular ForeignKey case. Test runner AppRegistryNotReady prevented test execution. Modifying _get_non_gfk_field was insufficient — root cause is in the check function.
