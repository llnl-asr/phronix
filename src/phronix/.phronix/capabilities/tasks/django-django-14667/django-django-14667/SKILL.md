---
name: django-django-14667
description: What problem a later run would recognize about this Django QuerySet defer/only chaining bug
subject: django-django-14667
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | what-problem-it-solves |
| `I2` | Instructions | key-idea |
| `I3` | Instructions | instructions-to-solve |
| `I4` | Instructions | Constraints and Rules |
| `I5` | Instructions | Pitfalls and Lessons |
| `R1` | Rules | constraints-rules |

## Instructions

### I1 — what-problem-it-solves

The skill fixes QuerySet.defer() not clearing deferred fields when chaining with .only(). When a user chains .only("name").defer("name"), the field "name" ends up loading all fields instead of just the deferred ones. The issue is that add_deferred_loading's defer=False branch only removes fields from the immediate set but doesn't add them to the deferred set, resulting in (frozenset(), False) which means "neither immediate nor deferred" and ALL fields load.

### I2 — key-idea

The key insight is that the defer=False branch of add_deferred_loading() has two responsibilities: (1) remove field names from the "immediate load" set (done correctly), and (2) add those field names to the "deferred load" set (not done). Simply toggling the boolean flag doesn't achieve the proper transition from immediate to deferred loading. The fix must both remove from immediate AND add to deferred when transitioning from .only() + .defer().

### I3 — instructions-to-solve

1. In django/db/models/sql/query.py, find the add_deferred_loading method (around lines 2071-2090).
2. The defer=False branch currently reads:
      self.deferred_loading = existing.difference(field_names), False
   This only removes fields from the immediate set but does NOT add them to the deferred set.
3. Change this to properly handle the transition from immediate (set by .only()) to deferred (via .defer()):
      self.deferred_loading = existing.union(field_names), True
   This adds the field names to the deferred set AND sets defer=True, so the fields are properly deferred instead of loading all fields.
4. Also verify that add_immediate_loading's defer=False branch correctly removes from immediate while respecting existing deferrals (it already does this correctly per the docstring).
5. Run the target test test_defer_only_chaining to confirm the fix passes.

### I4 — Constraints and Rules

- All existing regression tests must continue to pass (28 of 29 currently pass).
- The change must not affect other deferred/only behavior; only the handling of `add_deferred_loading` is altered.
- Preserve the method signature and existing comment structure.

### I5 — Pitfalls and Lessons

- Previously attempting to toggle the defer flag based on prior `defer` state caused the method to remove fields from immediate‑loading instead of always deferring them, leading to the bug persisting.
- Ensure the method always sets the second tuple element to `True`; omitting this reintroduces the issue.
- Do not modify surrounding logic for `add_immediate_loading`; it remains unchanged.

## Rules

### R1 — constraints-rules

Constraints and rules derived from what worked in previous attempts:
1. The defer=False branch in add_deferred_loading must both remove from immediate AND add to deferred — toggling the boolean flag alone is insufficient.
2. The correct fix changes the line from:
      self.deferred_loading = existing.difference(field_names), False
   to:
      self.deferred_loading = existing.union(field_names), True
   This ensures field names are added to the deferred set and the defer flag is properly set.
3. add_immediate_loading's defer=False branch already correctly removes from the immediate set while respecting existing deferrals — no change needed there.
4. After the fix, run the target test test_defer_only_chaining to verify it passes, and ensure all 29 regression tests still pass.

## References

- `skill_load(name="django-django-14667", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
