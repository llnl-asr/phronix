---
name: sympy-24152
description: The sympy-24152 subject.
subject: sympy-24152
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Instructions to solve it |
| `R1` | Rules | Constraints |





## Instructions

### I1 — Problem description

TensorProduct expansion fails to distribute scalar factors, leading to incomplete results such as `2*U - V` in a tensor product not being fully expanded.

### I2 — Key idea

Separate commutative scalar factors from the TensorProduct, recursively expand the TensorProduct, then recombine the scalars.

### I3 — Instructions to solve it

1. Open `sympy/physics/quantum/tensorproduct.py`.
2. Locate the `_eval_expand_tensorproduct` method.
3. Replace its docstring with the expanded version handling scalar factors (lines 30‑38 in the diff).
4. Insert logic to split commutative and non‑commutative parts when a `Mul` result is produced (lines 107‑119).
5. Ensure the method returns `self` at the end (line 131).
6. Save the file and run the sympy test suite for quantum tensorproduct (`pytest sympy/physics/quantum/tests/test_tensorproduct.py`).

## Rules

### R1 — Constraints

- All existing sympy quantum tests must continue to pass.
- The method must still return the original TensorProduct when no addition is present.
- Scalar factors must remain correctly attached after expansion.
- No other parts of the file should be modified.

## References

- `skill_load(name="sympy-24152", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

