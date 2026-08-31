---
name: matplotlib-matplotlib-24149
description: Fix Axes.bar failure on all-NaN inputs in Matplotlib 3.6.1
subject: matplotlib-matplotlib-24149
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem it solves |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `I4` | Instructions | Constraints and rules |
| `I5` | Instructions | Pitfalls and lessons |

## Instructions

### I1 — Problem it solves

When all x values passed to `Axes.bar` are NaN, `Axes.bar` raises a `StopIteration` from `cbook._safe_first_finite`, causing test `test_bar_all_nan` to fail.

### I2 — Key idea

Guard the call to `cbook._safe_first_finite` so that all‑NaN inputs fall back to the original `x0` before the exception propagates.

### I3 — Instructions to solve it

1. Edit `lib/matplotlib/axes/_axes.py` in the `_convert_dx` method.
2. Extend the `except` clause to catch `StopIteration`.
3. In the new `except` block, keep `x0` unchanged (fallback to original) and `pass`.
4. Add a comment explaining the fallback for future maintainers.

### I4 — Constraints and rules

• All existing regression tests (767) must continue to pass.
• The fallback must not alter behavior for non‑NaN inputs.
• Do not introduce new imports; only modify the exception handling.
• Preserve the original semantics of `_convert_dx` for valid data.

### I5 — Pitfalls and lessons

• Adding `StopIteration` to the caught exceptions alone does not fix the bug because the exception occurs before the `try/except` block is reached.
• Any change must ensure the control flow reaches the fallback; merely extending the exception list without a fallback comment can still leave the error unhandled.
• Guarding the call itself (e.g., checking for all‑NaN before calling `_safe_first_finite`) is an alternative approach if future modifications are needed.

## Rules
