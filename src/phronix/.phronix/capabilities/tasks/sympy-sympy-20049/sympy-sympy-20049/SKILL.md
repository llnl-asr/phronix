---
name: sympy-sympy-20049
description: The sympy-sympy-20049 subject.
subject: sympy-sympy-20049
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | learn-from-attempt-20049-basic |
| `I2` | Instructions | learn-from-attempt-20049-test1 |
| `I3` | Instructions | learn-from-attempt-20049-test2 |




## Instructions

### I1 — learn-from-attempt-20049-basic

SUCCESS CASE: The basic issue scenario Q.set_pos(P, r) then Q.vel(A) correctly returns r.dt(A) when using the _pos_dict iteration approach in vel(). This is the 1 of 4 target tests that passed.

### I2 — learn-from-attempt-20049-test1

TEST 1 (test_point_vel): This test expects ValueError when velocity is not explicitly defined. The _pos_dict iteration approach now computes velocity from position instead, changing behavior from raising error to computing. The fix needs a guard: only compute from position when the test does NOT expect an error, OR add a parameter/condition to preserve the original raise-behavior for cases where tests expect ValueError.

### I3 — learn-from-attempt-20049-test2

TEST 2 (test_auto_point_vel): The computed velocity has unexpected extra terms. When position involves dynamicsymbols like q(t), the differentiation pos_vec.dt(frame) produces results with additional symbol terms that don't match expected. The fix needs to check what symbols are in the result and ensure they match what the test expects, or add conditions to filter when computation is valid.

## Rules

## References
