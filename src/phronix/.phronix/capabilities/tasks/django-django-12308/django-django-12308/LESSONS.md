# Lessons — django-django-12308

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — Pitfalls

- Using `json.dumps` directly skips `InvalidJSONInput` handling and can raise errors.
- Re‑applying the same unchanged code yields no progress and wastes time.
- Not catching exceptions leads to test failures for complex JSON values.

## Lessons

### L1 — Failed JSONField display fix

**2026-08-29** — Attempt 1 added JSONField handling in admin utils but used fallback `display_for_value`, resulting in output `{'a': {'b': 'c'}}` instead of JSON string `{"a": {"b": "c"}}`. This caused test failures `test_json_display_for_field` in `admin_utils.tests.UtilsTests`. The fix must ensure proper JSON string formatting.
