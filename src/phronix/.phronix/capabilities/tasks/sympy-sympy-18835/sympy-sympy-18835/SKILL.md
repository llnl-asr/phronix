---
name: sympy-sympy-18835
description: The sympy-sympy-18835 subject.
subject: sympy-sympy-18835
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Diagnosis: uniq list modification detection |


## Instructions

### I1 — Diagnosis: uniq list modification detection

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

## References
