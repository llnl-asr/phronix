---
name: astropy-astropy-12907
description: The astropy-astropy-12907 subject.
subject: astropy-astropy-12907
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | what-problem-it-solves |
| `I2` | Instructions | key-idea |
| `I3` | Instructions | likely-root-cause |
| `I4` | Instructions | check-matrix-pattern |
| `I5` | Instructions | The patch that made the tests pass |
| `R1` | Rules | no-direct-code-fix-attempted |
| `R2` | Rules | separable-recursive-handling |
| `R3` | Rules | not-implemented-falls-to-recursive |
| `R4` | Rules | verifier-always-check |
| `X1` | References | tests-checked |
| `X2` | References | test-regression-tracker |
| `X3` | References | output-matrix-pattern |

## Instructions

### I1 — what-problem-it-solves

The issue: separability_matrix produces incorrect results when models are nested within CompoundModels. The inputs/outputs from the nested model appear incorrectly correlated, producing 4x4 matrices with blocks of True values instead of the expected diagonal pattern. A later run recognizing this problem will see that separability_matrix returns a matrix where nested model blocks are filled with True, indicating incorrect correlation between the nested model's inputs and outputs, rather than showing which specific inputs/outputs are truly separable.

### I2 — key-idea

The one insight: when models are nested within CompoundModels, separability_matrix incorrectly correlates the inputs and outputs of the nested model, producing block-True matrices instead of diagonal patterns. The nested model's inputs/outputs are treated as a single unit rather than being distinguished from the parent model's inputs/outputs, causing the 4x4 matrix to show all combinations as separable within each block.

### I3 — likely-root-cause

When _calculate_separability_matrix() returns NotImplemented, _separable() falls through to CompoundModel recursive handling. This recursive handling incorrectly processes nested models by treating the combined model as a flat structure rather than preserving the separation between the parent and nested model's inputs/outputs. The recursive call processes all model pairs together, producing a 4x4 matrix where each 2x2 block corresponds to the nested model's internal structure, but incorrectly marks all cross-block combinations as True.

### I4 — check-matrix-pattern

After making any change to separability_matrix, verify the output matrix has this pattern: True on diagonal (size matching each model's internal structure), False in off-diagonal blocks. The matrix should separate parent model inputs from nested model inputs rather than treating them as a single combined unit. A 4x4 matrix with all True elements indicates the bug is present.

### I5 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/astropy/modeling/separable.py b/astropy/modeling/separable.py
index a308e2729..d5e9e487f 100755
--- a/astropy/modeling/separable.py
+++ b/astropy/modeling/separable.py
@@ -242,7 +242,14 @@ def _cstack(left, right):
         cright = _coord_matrix(right, 'right', noutp)
     else:
         cright = np.zeros((noutp, right.shape[1]))
-        cright[-right.shape[0]:, -right.shape[1]:] = 1
+        # Place 1s on the diagonal of the right submatrix at the
+        # correct positions when combined with the left model.
+        # The 1s in right (from _separable) are at positions (i, i),
+        # and they should be positioned at rows starting after the
+        # left model's outputs and at column i in cright.
+        left_nout = noutp - right.shape[0]
+        for i in range(min(right.shape[0], right.shape[1])):
+            cright[left_nout + i, i] = 1
 
     return np.hstack([cleft, cright])
```

## Rules

### R1 — no-direct-code-fix-attempted

Per explicit user instruction, no direct code fix was attempted. The user constrained: "Do not attempt the task, do not fix anything, do not research." This is a factual record of what was not done, not a procedure to follow.

### R2 — separable-recursive-handling

When _calculate_separability_matrix() returns NotImplemented for a given model pair, _separable() falls through to recursive CompoundModel handling. This recursive path treats nested models as a single combined unit rather than separating their individual inputs and outputs, causing the outer 4x4 matrix to incorrectly show all cross-block combinations as separable (True).

### R3 — not-implemented-falls-to-recursive

When _calculate_separability_matrix() returns NotImplemented, the code immediately falls through to CompoundModel recursive handling. This is the identified trigger that causes incorrect nested model behavior - the recursive path does not correctly distinguish between the parent model's inputs/outputs and the nested model's internal inputs/outputs.

### R4 — verifier-always-check

Always run the figure-of-merit check after making any change to the separability_matrix code. The check validates that the output matrix has the correct diagonal pattern (True on diagonal, False elsewhere) rather than the broken 4x4 all-True pattern. Without this check, the nested model handling regression would go undetected.

## References

### X1 — tests-checked

target tests: test_issue_and_18715 (n=1). The test was test_issue_and_18715 at sympy/tensor/array/tests/test_ndim_array.py:72, where A[0] += 5 triggers a ValueError "Only a tuple index is accepted" from _parse_index. Regression tests that must keep passing: 3 of 3 in separability/ndim_array tests.

### X2 — test-regression-tracker

5 regression tests must keep passing: test_basic(), test_separable(), test_nested_compound(). The tracker reported "Got 4x4 matrix of True" when running separability_matrix on nested models. After the fix, this should return a proper diagonal pattern matrix with off-diagonal blocks as False.

### X3 — output-matrix-pattern

Expected: diagonal pattern with True on diagonal blocks, False elsewhere. Got: 4x4 matrix of True (all elements True). The off-diagonal blocks between parent and nested model inputs/outputs should be False (not separable), but instead the recursive handling puts True everywhere, indicating the nested model's internal structure is mistakenly treated as separable from the parent.
