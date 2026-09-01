---
name: sympy-sympy-16988
description: The sympy-sympy-16988 subject.
subject: sympy-sympy-16988
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Intersection deduplication fix - problem statement |
| `I2` | Instructions | Intersection deduplication fix - key idea |
| `I3` | Instructions | Intersection deduplication fix - instructions |
| `I4` | Instructions | Intersection deduplication fix - constraints |
| `I5` | Instructions | Intersection deduplication fix - pitfalls |






## Instructions

### I1 — Intersection deduplication fix - problem statement

**What problem it solves:**

When `Intersection({1},{1},{x})` is called, it returns `EmptySet()` instead of `{1}`. Duplicates passed to Intersection at instantiation are not removed, causing incorrect results. Someone arriving with a failing intersection test should recognize this skill by the symptom: duplicate sets in Intersection constructor return wrong results.

### I2 — Intersection deduplication fix - key idea

**The key idea:**

Duplicates must be removed at the outset of Intersection.__new__ instantiation, BEFORE the evaluate check, to ensure canonical processing regardless of the evaluate flag. The deduplication uses sympy.sets.sets.ordered() for canonical ordering followed by a seen-list dedup pattern.

### I3 — Intersection deduplication fix - instructions

**Instructions to solve it:**

1. In sympy/sets/sets.py, locate Intersection.__new__ method
2. After line `args = _sympify(args)`, insert deduplication block:
   ```
   # Deduplicate args while preserving canonical order
   # This ensures Intersection({1},{1},{x}) gives the same result as Intersection({1},{x})
   from sympy.sets.sets import ordered as set_ordered
   args = list(set_ordered(args, Set._infimum_key))
   seen = []
   deduped = []
   for arg in args:
       if arg not in seen:
           seen.append(arg)
           deduped.append(arg)
   args = deduped
   ```
3. The old `args = list(ordered(args, Set._infimum_key))` at the end of the method is now redundant and should be removed (it was the original ordering call that deduplication replaced).

### I4 — Intersection deduplication fix - constraints

**Constraints and rules:**

- Deduplication MUST happen BEFORE the `if evaluate:` check, because global_evaluate[0] is True by default, which causes the original code to return early from the evaluate branch
- The fix must not regress any previously working test cases
- Must handle both evaluate=True and evaluate=False cases correctly
- The old ordering line at the method end becomes unnecessary after this change

### I5 — Intersection deduplication fix - pitfalls

**Pitfalls and lessons:**

- Initial attempt placed deduplication AFTER the evaluate check, but it was skipped because evaluate=True (default) caused early return - this is the most valuable lesson: always place dedup before the evaluate check
- The pytest collection error `AttributeError: module 'py' has no attribute 'test'` is a pre-existing environment incompatibility, NOT caused by this fix - both attempts' target tests fail due to this, not due to incorrect fix implementation
- Manual verification confirmed the fix works: `Intersection({1},{1},{x})` → `FiniteSet(1)` matches `Intersection({1},{x})` → `{1}`
- Multiple/mixed duplicates handled correctly after fix
- No duplicates still work correctly after fix
- The fix was verified with these key cases from the tracker:
  - Intersection({1},{1},{x}) → FiniteSet(1) ✓
  - Intersection({1},{x}) → {1} ✓
  - Intersection({1},{1}) → {1} ✓
  - Intersection(Interval(1,3), Interval(2,4)) → Interval(2, 3) ✓
  - Intersection(FiniteSet(1,2,3), Interval(2,5), evaluate=False) returns unevaluated form ✓

## Rules

## References
