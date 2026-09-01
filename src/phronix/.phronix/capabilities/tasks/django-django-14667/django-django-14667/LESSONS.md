# Lessons — django-django-14667

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

### L1 — pitfalls-and-lessons

**2026-08-29** — Pitfalls and lessons from what did not work in previous attempts:
1. **Attempt 1 tried**: Changing False to True in `self.deferred_loading = existing.difference(field_names), False`. This only toggled the flag but didn't add fields to the deferred set. The test still failed because `(frozenset(), True)` means "no fields deferred" which still loads everything.
2. **Attempt 2 tried**: Changing to `self.deferred_loading = existing.union(field_names), True`. This was the correct approach but was not properly documented/recorded. The test pattern shows this should work — the approach was correct but the reasoning about WHY was insufficiently captured for later runs.
3. **The core reason both attempts failed**: The `defer=False` branch of `add_deferred_loading()` has two jobs: remove from immediate AND add to deferred. Only toggling the flag addresses job 1 but not job 2. The fix `existing.union(field_names), True` addresses both by adding to the deferred set AND setting the flag correctly.
4. **Most valuable thing recorded** (from attempt-1/exchange.md): "why the approach above was insufficient" — this is the key lesson for later runs: the False→True flag toggle alone is insufficient; the set operation itself must change.
5. **Regression tests**: All 29 regression tests must continue to pass after the fix. This means the fix should only affect the specific defer/only chaining scenario and not break any other loading mode combinations.
