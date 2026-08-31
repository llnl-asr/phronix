---
name: scikit-learn-scikit-learn-15512
description: Fix affinity propagation non-convergence return values. When the algorithm doesn't converge, the else clause of the for loop sets labels and cluster_centers_indices to -1/empty, but then falls through to post-loop code that recomputes them incorrectly. Added return statements in the else clause to return early with correct values.
subject: scikit-learn affinity propagation non-convergence fix
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Identify failing behavior |
| `I2` | Instructions | Edit source |
| `I3` | Instructions | Run tests |
| `I4` | Instructions | Fix affinity propagation non-convergence return values |
| `R1` | Rules | Do not alter test files |
| `R2` | Rules | Preserve existing functionality |
| `R3` | Rules | Why return early in non-convergence else clause |

## Instructions

### I1 — Identify failing behavior

Run the AffinityPropagation example with low max_iter to reproduce non-convergence and observe that cluster_center_indices is non-empty and labels are not -1.

### I2 — Edit source

Modify `sklearn/cluster/_affinity_propagation.py` after the convergence loop: if no exemplars were found (K == 0), set `cluster_centers_indices = np.array([])` and `labels = np.full(n_samples, -1, dtype=int)`.

### I3 — Run tests

Execute the scikit-learn test suite for AffinityPropagation to ensure the fix passes.

### I4 — Fix affinity propagation non-convergence return values

When the affinity propagation algorithm in sklearn/cluster/_affinity_propagation.py does not converge (the for loop completes without break), the else clause must return early with the correct values. Without explicit return statements, the code falls through to post-loop code (lines 212-239) that recomputes labels and cluster_centers_indices based on E and K, producing incorrect results instead of the -1/empty values the documentation specifies.

The fix: In the else clause (after line 200, the for-loop else), add:
1. A ConvergenceWarning
2. labels = np.array([-1] * n_samples)
3. cluster_centers_indices = []
4. if return_n_iter: return cluster_centers_indices, labels, max_iter
   else: return cluster_centers_indices, labels

This prevents fall-through to the convergence code that would compute wrong cluster assignments.

## Rules

### R1 — Do not alter test files

All changes must be confined to source code; test files remain unchanged.

### R2 — Preserve existing functionality

The fix must not affect cases where AffinityPropagation converges normally.

### R3 — Why return early in non-convergence else clause

The for-loop else clause in affinity_propagation runs when the algorithm doesn't converge within max_iter iterations. Without explicit return statements, execution falls through to post-loop code (I = np.flatnonzero(E); K = I.size; if K > 0: compute labels/centers) which recomputes cluster assignments. This produces WRONG results when the algorithm didn't converge - it may return non-empty cluster_centers_indices and labels that are not all -1, contradicting the documented behavior: "When the algorithm does not converge, it returns an empty array as cluster_center_indices and -1 as label for each training sample."

Always add return statements in the else clause to prevent fall-through. The returned values must be: empty cluster_centers_indices and -1 labels for all n_samples, optionally including max_iter as the third element when return_n_iter=True.

## References
