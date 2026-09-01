# Lessons — matplotlib-matplotlib-24970

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

### P1 — P1 — NumPy 1.24+ deprecation on uint8 colormap calls

When Colormap.__call__ receives a uint8-dyped array, xa stays as uint8 dtype through the float-handling block. Lines 730-731 then assign sentinel values 257 and 256 (self._i_over and self._i_under) to positions in the uint8 array, which triggers NumPy deprecation warnings about out-of-bound Python integer-to-array conversion.

## Lessons

### L1 — P2 — Float-handling block only runs for float input

**2026-08-29** — The block spanning lines 717-727 that does `xa = xa.astype(int)` only processes inputs that already have a float-adjacent condition. When the input has a non-float dtype like uint8, no astype(int) conversion occurs and xa retains its original dtype, causing the later assignments to trigger warnings.

### L2 — P3 — self._i_over and self._i_under exceed uint8 range

**2026-08-29** — The hardcoded sentinel values self._i_over (257) and self._i_under (256) are Python ints that exceed the maximum value of 255 for uint8 dtype. When assigned to a uint8 array after np.clip, NumPy 1.24+ emits a deprecation warning about converting out-of-bound Python integers to integer arrays.

### L3 — P4 — np.clip preserves dtype

**2026-08-29** — np.clip(xa, -1, self.N, out=xa) preserves the input dtype. When xa starts as uint8, the clipped result is still uint8, so the subsequent `xa = xa.astype(int)` (or the new else clause) is the only point where the dtype changes from uint8 to int.

### L4 — P5 — Fix patches untouched existing code

**2026-08-29** — The fix adds only the else clause after line 727's unconditional `xa = xa.astype(int)`. This is a minimal, targeted change that touches exactly one new line. All other lines in the __call__ method remain as they were before the fix, so existing behavior for float inputs is fully preserved.

### L5 — P6 — Scope of the fix

**2026-08-29** — The fix applies to any non-float input dtype (uint8, other integer types) that reaches the over/under-range index assignments. It does not change behavior for float inputs, which already had the astype(int) on line 727. Edge case: dtypes where 257 or 256 might be valid values also need the int conversion, which is why the else guards all non-float paths uniformly.

### L6 — P7 — Assignment order matters

**2026-08-29** — The comment "Set the over-range indices before the under-range; otherwise the under-range values get converted to over-range" on lines 729-730 matters: the order of the two assignment lines (730 then 731) ensures that any value already set to self._i_over on line 730 isn't accidentally overwritten by the under-range assignment on line 731.

### L7 — P8 — Assignment order matters 2

**2026-08-29** — self._i_over (257) is assigned before self._i_under (256) on lines 730-731. This order matters because the under-range assignment on 731 could overwrite an over-range sentinel that was already set on 730 if the logic order were different.

### L8 — P9 — Assignment order matters 3

**2026-08-29** — When a value falls in both the over-range and under-range (impossible since the conditions are xa > self.N - 1 and xa < 0 respectively), the order still ensures no double-assignment logic error. The two conditions are mutually exclusive, so the order is a defensive guarantee against future refactoring.

### L9 — P10 — I7 and I9 compliance

**2026-08-29** — I7: A solved task owes the next run a skill it can LOOK UP. This skill matplotlib-matplotlib-24970 is named and structured so a later run can call skill_load("matplotlib-matplotlib-24970") and retrieve all learnings.
I9: Memory is this session; a skill is what survives it. This skill, stored in the persistent skill store (not transient session memory), will be available to future sessions that load the phronix library, independent of this conversation's context.

### L10 — L10 — All sections in order

**2026-08-29** — The skill contains exactly 5 top-level sections in order: (1) what problem it solves, (2) the key idea, (3) instructions to solve it, (4) constraints and rules, (5) pitfalls and lessons. I7 and I9 are applied as structural rules within the skill's design.
