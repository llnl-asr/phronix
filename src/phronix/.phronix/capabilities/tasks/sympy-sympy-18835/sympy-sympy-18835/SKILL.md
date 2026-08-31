---
name: sympy-sympy-18835
description: The sympy-sympy-18835 subject.
subject: sympy-sympy-18835
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix uniq to raise RuntimeError on size change |
| `I2` | Instructions | Symptom description for later runs |
| `I3` | Instructions | Diagnosis: uniq list modification detection |
| `R1` | Rules | Maintain existing test behavior |

## Instructions

### I1 — Fix uniq to raise RuntimeError on size change

1. Open `sympy/utilities/iterables.py`.
2. Locate the `uniq` function definition.
3. Add a docstring explaining the new behaviour and the RuntimeError.
4. At the start of the function, try to record the initial length of the sequence:
   ```python
   try:
       initial_len = len(seq)
   except Exception:
       initial_len = None
   ```
5. Inside the loop, after obtaining each element, check if the length has changed:
   ```python
   if initial_len is not None and len(seq) != initial_len:
       raise RuntimeError("Sequence size changed during iteration")
   ```
6. Keep the existing logic for yielding unique elements.
7. Ensure the function still works for unhashable elements by retaining the fallback `except TypeError` block.
8. Save the file.
9. Run the full test suite; `test_uniq` should now raise `RuntimeError` when the input list size changes during iteration.

### I2 — Symptom description for later runs

When `uniq` is used on a mutable sequence and the sequence size changes during iteration, the test `test_uniq` expects a `RuntimeError` similar to Python's native error for modifying a list during iteration. The current implementation does not raise this error, causing the test to fail.

**Why this belongs in a skill:** This description is the problem statement that later agents will match against to decide if this skill applies.

### I3 — Diagnosis: uniq list modification detection

What problem it solves:
uniq() silently allows list modifications during iteration, producing incorrect results without warning. Future agents need to detect and handle this.

The key idea:
If a list's length changes during uniq() iteration, raise RuntimeError similar to Python's dict modification behavior.

Instructions (200 chars max):
1. Record seq_len before loop in uniq()
2. After each iteration, check if len(seq) != seq_len
3. If changed and checkable, raise RuntimeError("Sequence modified during iteration")
4. Wrap in try/except TypeError for non-sequence iterables

Constraints:
- 41 regression tests must keep passing
- RuntimeError only when length actually changes
- Skip len() check for generators/iterators

Pitfall (100 chars max):
Attempt-1 added length check but test_uniq failed — RuntimeError not raised because check logic was flawed or placement incorrect. Test at test_iterables.py:707 expects raises(RuntimeError, lambda: [f.remove(i) for i in uniq(f)]).

## Rules

### R1 — Maintain existing test behavior

The `uniq` function must continue to yield unique elements correctly for all inputs, including unhashable elements and iterables without a length. The added size‑change detection must not alter the original uniqueness logic or raise errors for sequences whose size is immutable during iteration.

**Why:** The test suite has 41 regression tests; any change breaking existing behavior would cause failures unrelated to the target issue.

## References
