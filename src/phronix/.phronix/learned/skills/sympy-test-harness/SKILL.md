---
name: sympy-test-harness
description: How sympy's own test suite is actually run, to avoid false "failures" caused by the wrong runner.
subject: sympy-test-harness
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Do not run sympy tests with pytest |


## Instructions

## Rules

### R1 — Do not run sympy tests with pytest

Sympy is not set up for `pytest`; invoking `pytest` in this repo's testbed env fails with "No module named pytest". Use sympy's own runner instead: `bin/test <path>` or `python -c "import sympy; sympy.test('sympy/physics/units/...')"`. An attempt-2 grading run on sympy__sympy-24066 reported the target test as failing purely because of this missing-module error, not because the code fix was wrong — the underlying fix was independently verified correct by reproducing the issue's script directly with `python -c ...`. When a grading log shows "No module named pytest", treat the verdict as inconclusive for correctness and re-verify with the actual repro script or bin/test before concluding the fix is bad.

## References
