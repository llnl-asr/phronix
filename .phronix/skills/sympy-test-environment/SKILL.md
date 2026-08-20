---
name: sympy-test-environment
description: The sympy-test-environment subject.
subject: sympy-test-environment
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | This testbed has no pytest module — don't invoke pytest directly |


## Instructions

## Rules

### R1 — This testbed has no pytest module — don't invoke pytest directly

Running `pytest` in this repo's testbed fails with `No module named pytest`, even for correct code changes — this is an environment gap, not evidence the fix is wrong.

Why: attempt-2 on sympy__sympy-21847 produced a logically correct fix but was judged "0 target tests passed" solely because the harness's pytest invocation errored before running any test.

How to apply: before concluding a fix is wrong because "the target test failed," check whether the failure is `No module named pytest` (infra) vs an actual assertion/traceback from the test body. If it's the former, prefer sympy's own runner instead: `python -m sympy.testing.runtests <module>` or `bin/test <path>`. Don't revert or keep changing correct logic in response to a pytest-import failure.

## References
