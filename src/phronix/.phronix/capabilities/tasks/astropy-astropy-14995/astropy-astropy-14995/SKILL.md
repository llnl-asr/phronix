---
name: astropy-astropy-14995
description: Fix mask propagation in NDArithmeticMixin._arithmetic_mask: when one operand lacks a mask but the other has one, copy the existing mask to the result rather than passing None to handle_mask which causes TypeError. The fix adds `elif operand.mask is None: return deepcopy(self.mask)` before the else clause in _arithmetic_mask method of astropy/nddata/mixins/ndarithmetic.py.
subject: astropy-astropy-14995
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | I1 |
| `I2` | Instructions | R1 |
| `I3` | Instructions | What problem it solves |
| `I4` | Instructions | The key idea |
| `I5` | Instructions | Instructions to solve it |
| `I6` | Instructions | Constraints and rules |





## Instructions

### I1 — I1

Fix mask propagation in NDArithmeticMixin._arithmetic_mask: when one operand lacks a mask but the other has one, copy the existing mask to the result rather than passing None to handle_mask which causes TypeError.

### I2 — R1

In astropy/nddata/mixins/ndarithmetic.py, the _arithmetic_mask method now has an `elif operand.mask is None:` branch (line 525) that returns `deepcopy(self.mask)` when operand.mask is None but self.mask is not None. This handles the case where self has a mask but operand doesn't, preventing TypeError when handle_mask is called with None operand.mask.

### I3 — What problem it solves

The symptom is a TypeError when calling arithmetic operations on NDData objects where one operand has a mask and the other doesn't. Specifically, `TypeError: unsupported operand type(s) for |: 'int' and 'NoneType'` occurs when `np.bitwise_or(mask, None)` is called in `_arithmetic_mask()`. The failing test is `astropy/nddata/mixins/tests/test_ndarithmetic.py::test_nddata_bitmask_arithmetic`. This is the core mask-propagation gap in `NDArithmeticMixin._arithmetic_mask()` in `astropy/nddata/mixins/ndarithmetic.py`.

### I4 — The key idea

When one operand lacks a mask in _arithmetic_mask(), the existing mask should be copied to the result — not passed to handle_mask() which would fail with None. The one insight the whole fix turns on: if self has a mask but operand.mask is None, return deepcopy(self.mask) rather than calling handle_mask(self.mask, None). This is symmetric with the existing branch that handles self.mask is None and operand is not None (which returns deepcopy(operand.mask)).

### I5 — Instructions to solve it

In astropy/nddata/mixins/ndarithmetic.py, in the _arithmetic_mask() method, add the following branch before the final else clause (after line 527, the `elif operand is None:` check):

elif operand.mask is None:
    # Make a copy so there is no reference in the result.
    return deepcopy(self.mask)

This handles the case where self has a mask but operand.mask is None. Previously, the code would fall through to the else clause `return handle_mask(self.mask, operand.mask, **kwds)` which fails with TypeError when operand.mask is None because np.bitwise_or(mask, None) is not supported. The fix returns a copy of self's mask instead, matching the symmetry of the existing `elif self.mask is None and operand is not None:` branch which returns `deepcopy(operand.mask)`.

After this change, verify that 179 of 179 regression tests in the ndarithmetic test suite still pass, and the previously broken case (one operand with mask, one without) now works without TypeError.

### I6 — Constraints and rules

The fix must:
1. Only modify `astropy/nddata/mixins/ndarithmetic.py` in the `_arithmetic_mask()` method.
2. Add a single `elif operand.mask is None:` branch before the final `else` clause.
3. Return `deepcopy(self.mask)` from the new branch to avoid reference sharing.
4. Not change any existing conditions or existing branches.
5. Preserve backward compatibility: all 179 regression tests in the ndarithmetic test suite must still pass.
6. The fix must handle the case where `self.mask is not None` AND `operand.mask is None` — this is the only gap in the current if-elif-else chain.
7. Match the pattern used by the existing `elif self.mask is None and operand is not None:` branch, which returns `deepcopy(operand.mask)`.
8. Not introduce a new test file or modify test infrastructure.
9. The root cause is a TypeError when `np.bitwise_or(mask, None)` is called in the `handle_mask` call in the else branch.

## Rules
