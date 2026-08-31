---
name: sympy-sympy-24152
description: The sympy-sympy-24152 subject.
subject: sympy-sympy-24152
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | The key idea |
| `I3` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints and rules |

## Instructions

### I1 — What problem it solves

When a TensorProduct contains summands with scalar (commutative) factors, the expand(tensorproduct=True) method produces incomplete results. The expansion stops after distributing over the top-level addition but does not expand the summands within each tensor factor. For example, TensorProduct(2*U - V, U + V).expand(tensorproduct=True) returns 2*Ux(U + V) - Vx(U + V) instead of the complete 2*UxU + 2*UxV - VxU - VxV.

### I2 — The key idea

The core insight is that `TensorProduct.__new__` returns a `Mul` object containing both scalar factors and the tensor product when scalar factors are present, so the original `isinstance(tp, TensorProduct)` check fails for these cases. Using `args_cnc()` properly separates commutative (scalar) factors from the non-commutative part that contains the `TensorProduct`, enabling complete expansion in a single call.

### I3 — Instructions to solve it

1. In `sympy/physics/quantum/tensorproduct.py`, find the `_eval_expand_tensorproduct` method (around line 246).

2. Inside the loop `for aa in args[i].args:`, after the line `tp = TensorProduct(*args[:i] + (aa,) + args[i + 1:])`, replace the original check and processing:
   - Original: `if isinstance(tp, TensorProduct): tp = tp._eval_expand_tensorproduct(); add_args.append(tp)`
   - Replace with:
     ```
     c_part, nc_part = tp.args_cnc() #added
     if len(nc_part)==1 and isinstance(nc_part[0], TensorProduct): #modified
         nc_part = (nc_part[0]._eval_expand_tensorproduct(), ) #modified
     add_args.append(Mul(*c_part)*Mul(*nc_part)) #modified
     ```

3. The `args_cnc()` call splits commutative (scalar) factors from the non-commutative part. When `tp` is a plain `TensorProduct`, `c_part` is empty and `nc_part` contains the `TensorProduct`. When `tp` is a `Mul` with scalar factors (e.g., `2*Ux(U + V)`), `c_part` contains the scalars and `nc_part` contains the `TensorProduct`.

4. The non-commutative part is recursively expanded, and the result is recombined with the commutative factors using `Mul(*c_part)*Mul(*nc_part)`.

## Rules

### R1 — Constraints and rules

- The fix must use `args_cnc()` to separate scalar factors from the TensorProduct part, NOT a simple `isinstance(tp, TensorProduct)` check.
- The `len(nc_part)==1 and isinstance(nc_part[0], TensorProduct)` guard must remain to handle cases where the constructor returns 0 (e.g., `TensorProduct(U-U, U+V)` has no TensorProduct).
- After the fix, all 8 existing tests in `test_tensorproduct.py` must continue to pass.
- The fix must handle both cases: (a) plain `TensorProduct` with no scalar factors, and (b) `Mul` with scalar factors returned by the constructor.
- The `qapply()` function should also benefit from this fix as a downstream effect.

## References

- `skill_load(name="sympy-sympy-24152", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.
