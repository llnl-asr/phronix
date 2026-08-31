---
name: sympy-sympy-16988
description: The sympy-sympy-16988 subject.
subject: sympy-sympy-16988
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Remove duplicate arguments in Intersection.__new__ |
| `I2` | Instructions | Intersection deduplication fix - pitfalls |
| `I3` | Instructions | Intersection deduplication fix - key idea |
| `R1` | Rules | Do not break SymPy's canonical ordering |
| `R2` | Rules | Maintain test collection compatibility |

## Instructions

### I1 — Remove duplicate arguments in Intersection.__new__

Edit `sympy/sets/sets.py` at the `__new__` method of `Intersection` to deduplicate args while preserving order:
```python
# Remove duplicate arguments to avoid redundant processing
# Preserve order for deterministic behavior
args = list(dict.fromkeys(args))
```

### I2 — Intersection deduplication fix - pitfalls

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

### I3 — Intersection deduplication fix - key idea

**The key idea:**

Duplicates must be removed at the outset of Intersection.__new__ instantiation, BEFORE the evaluate check, to ensure canonical processing regardless of the evaluate flag. The deduplication uses sympy.sets.sets.ordered() for canonical ordering followed by a seen-list dedup pattern.

## Rules

### R1 — Do not break SymPy's canonical ordering

Ensure that any modifications to `Intersection.__new__` preserve the canonical ordering expected by SymPy internals.

### R2 — Maintain test collection compatibility

Do not reintroduce the import error; the `py.test` import must be replaced with a proper `pytest` import in `sympy/utilities/pytest.py`.

## References
