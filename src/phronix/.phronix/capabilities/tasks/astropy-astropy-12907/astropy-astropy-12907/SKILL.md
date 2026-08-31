---
name: astropy-astropy-12907
description: The astropy-astropy-12907 subject.
subject: astropy-astropy-12907
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Fix _cstack right placement |
| `I2` | Instructions | Problem description |
| `I3` | Instructions | key-idea |
| `I4` | Instructions | Instructions to solve |
| `I5` | Instructions | Problem Symptom |
| `I6` | Instructions | Instruction |
| `I7` | Instructions | Update separability matrix for nested CompoundModels |
| `I8` | Instructions | what-problem-it-solves |
| `I9` | Instructions | Instructions to implement fix |
| `I10` | Instructions | Constraints and rules |
| `I11` | Instructions | likely-root-cause |
| `I12` | Instructions | check-matrix-pattern |
| `R1` | Rules | Constraints |
| `R2` | Rules | Constraint |
| `R3` | Rules | Rule |
| `R4` | Rules | Skill naming convention |
| `R5` | Rules | no-direct-code-fix-attempted |
| `R6` | Rules | separable-recursive-handling |
| `R7` | Rules | not-implemented-falls-to-recursive |
| `R8` | Rules | verifier-always-check |

## Instructions

### I1 — Fix _cstack right placement

Replace the implementation of `_cstack` in `astropy/modeling/separable.py` with a block‑diagonal construction that correctly places the right‑hand side coordinate matrix. The new code should compute `noutp` via `_compute_n_outputs`, obtain `cleft` and `cright` as before, then build `result = np.block([[cleft, np.zeros((noutp, cright.shape[1]))], [np.zeros((noutp, cleft.shape[1])), cright]])` and return `result[:noutp]`. This fixes the SyntaxError and ensures separability is computed correctly.

```
def _cstack(left, right):
    noutp = _compute_n_outputs(left, right)
    if isinstance(left, Model):
        cleft = _coord_matrix(left, 'left', noutp)
    else:
        cleft = np.zeros((noutp, left.shape[1]))
        cleft[: left.shape[0], : left.shape[1]] = left
    if isinstance(right, Model):
        cright = _coord_matrix(right, 'right', noutp)
    else:
        cright = np.zeros((noutp, right.shape[1]))
        cright[: right.shape[0], : right.shape[1]] = right
    result = np.block([
        [cleft, np.zeros((noutp, cright.shape[1]))],
        [np.zeros((noutp, cleft.shape[1])), cright]
    ])
    return result[:noutp]
```

### I2 — Problem description

When a test fails due to `separability_matrix` handling nested `CompoundModel`s, the output matrix incorrectly places submatrices for right-hand side components, causing mismatched boolean values.

### I3 — key-idea

The one insight: when models are nested within CompoundModels, separability_matrix incorrectly correlates the inputs and outputs of the nested model, producing block-True matrices instead of diagonal patterns. The nested model's inputs/outputs are treated as a single unit rather than being distinguished from the parent model's inputs/outputs, causing the 4x4 matrix to show all combinations as separable within each block.

### I4 — Instructions to solve

1. Edit `astropy/modeling/separable.py`:
   - In `_coord_matrix`, replace the block that sets `mat[:model.n_outputs, : model.n_inputs] = 1` and `mat[-model.n_outputs:, -model.n_inputs:] = 1` with identity matrices:
     ```python
     if pos == 'left':
         mat[:model.n_outputs, :model.n_inputs] = np.eye(model.n_outputs, model.n_inputs, dtype=int)
     else:
         mat[-model.n_outputs:, -model.n_inputs:] = np.eye(model.n_outputs, model.n_inputs, dtype=int)
     ```
2. Ensure that for non-separable models, the identity block is placed correctly:
   ```python
   if pos == 'left':
       mat[:model.n_outputs, :model.n_inputs] = np.identity(model.n_inputs, dtype=mat.dtype)
   else:
       start = noutp - model.n_outputs
       mat[start:start + model.n_outputs, start:start + model.n_inputs] = np.identity(model.n_inputs, dtype=mat.dtype)
   ```
3. Add a compatibility shim in `astropy/utils/shapes.py` to handle NumPy 2.0 deprecation:
   ```python
   if not hasattr(np, 'core'):
       np.core = np._core  # type: ignore[attr-defined]
   ```
4. Run the test suite and verify that:
   - All target tests in `test_separable.py` now pass.
   - No regression tests fail.

### I5 — Problem Symptom

Separability matrix reports non‑separable inputs/outputs when a CompoundModel is nested, e.g., `separability_matrix(m.Pix2Sky_TAN() & cm)` returns true for cross terms.

### I6 — Instruction

No code change has been identified yet; further investigation of `separability_matrix` implementation is required before a fix can be applied.

### I7 — Update separability matrix for nested CompoundModels

In `astropy/modeling/separable.py`, modify the matrix assignment at line 123 to use `mat[-model.n_outputs:, :model.n_inputs] = m` instead of `mat[-model.n_outputs:, -model.n_inputs:] = m`. This correctly places the submatrix for the right-hand side components when handling nested CompoundModels.

### I8 — what-problem-it-solves

The issue: separability_matrix produces incorrect results when models are nested within CompoundModels. The inputs/outputs from the nested model appear incorrectly correlated, producing 4x4 matrices with blocks of True values instead of the expected diagonal pattern. A later run recognizing this problem will see that separability_matrix returns a matrix where nested model blocks are filled with True, indicating incorrect correlation between the nested model's inputs and outputs, rather than showing which specific inputs/outputs are truly separable.

### I9 — Instructions to implement fix



### I10 — Constraints and rules



### I11 — likely-root-cause

When _calculate_separability_matrix() returns NotImplemented, _separable() falls through to CompoundModel recursive handling. This recursive handling incorrectly processes nested models by treating the combined model as a flat structure rather than preserving the separation between the parent and nested model's inputs/outputs. The recursive call processes all model pairs together, producing a 4x4 matrix where each 2x2 block corresponds to the nested model's internal structure, but incorrectly marks all cross-block combinations as True.

### I12 — check-matrix-pattern

After making any change to separability_matrix, verify the output matrix has this pattern: True on diagonal (size matching each model's internal structure), False in off-diagonal blocks. The matrix should separate parent model inputs from nested model inputs rather than treating them as a single combined unit. A 4x4 matrix with all True elements indicates the bug is present.

## Rules

### R1 — Constraints

- All existing regression tests must continue to pass.
- The function must preserve behavior for non-nested CompoundModels.
- The changes must be compatible with NumPy >=2.0 (avoid deprecated np.core).

### R2 — Constraint

Do not modify Astropy core files until the root cause of the nested CompoundModel handling is understood; ensure existing tests continue to pass.

### R3 — Rule

Avoid repeating identical skill loads without new data; reuse existing analysis results to save runtime.

### R4 — Skill naming convention

Skill names must be kebab-case matching the repository identifier, e.g., `astropy-astropy-12907` for the Astropy issue task.

### R5 — no-direct-code-fix-attempted

Per explicit user instruction, no direct code fix was attempted. The user constrained: "Do not attempt the task, do not fix anything, do not research." This is a factual record of what was not done, not a procedure to follow.

### R6 — separable-recursive-handling

When _calculate_separability_matrix() returns NotImplemented for a given model pair, _separable() falls through to recursive CompoundModel handling. This recursive path treats nested models as a single combined unit rather than separating their individual inputs and outputs, causing the outer 4x4 matrix to incorrectly show all cross-block combinations as separable (True).

### R7 — not-implemented-falls-to-recursive

When _calculate_separability_matrix() returns NotImplemented, the code immediately falls through to CompoundModel recursive handling. This is the identified trigger that causes incorrect nested model behavior - the recursive path does not correctly distinguish between the parent model's inputs/outputs and the nested model's internal inputs/outputs.

### R8 — verifier-always-check

Always run the figure-of-merit check after making any change to the separability_matrix code. The check validates that the output matrix has the correct diagonal pattern (True on diagonal, False elsewhere) rather than the broken 4x4 all-True pattern. Without this check, the nested model handling regression would go undetected.

## References

### X1 — tests-checked

target tests: test_issue_and_18715 (n=1). The test was test_issue_and_18715 at sympy/tensor/array/tests/test_ndim_array.py:72, where A[0] += 5 triggers a ValueError "Only a tuple index is accepted" from _parse_index. Regression tests that must keep passing: 3 of 3 in separability/ndim_array tests.

### X2 — test-regression-tracker

5 regression tests must keep passing: test_basic(), test_separable(), test_nested_compound(). The tracker reported "Got 4x4 matrix of True" when running separability_matrix on nested models. After the fix, this should return a proper diagonal pattern matrix with off-diagonal blocks as False.

### X3 — output-matrix-pattern

Expected: diagonal pattern with True on diagonal blocks, False elsewhere. Got: 4x4 matrix of True (all elements True). The off-diagonal blocks between parent and nested model inputs/outputs should be False (not separable), but instead the recursive handling puts True everywhere, indicating the nested model's internal structure is mistakenly treated as separable from the parent.
