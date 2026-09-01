---
name: sympy-sympy-21847
description: The sympy-sympy-21847 subject.
subject: sympy-sympy-21847
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | sympy itermonomials min_degree filter bug |
| `I2` | Instructions | The patch that made the tests pass |
| `R1` | Rules | itermonomials min_degrees filter: max vs sum powers |

## Instructions

### I1 — sympy itermonomials min_degree filter bug

Problem: itermonomials uses max(powers.values()) >= min_degree to filter monomials by minimum degree, but this is incorrect. Should be sum(powers.values()) >= min_degree to filter by total degree.

Key idea: The function checks the maximum exponent of any single variable rather than the sum of all exponents (total degree), causing mixed monomials like x**2*y (total degree 3) to be incorrectly filtered out when min_degree=3.

Fix instruction:
- File: sympy/polys/monomials.py
- Line 130: Change if max(powers.values()) >= min_degree: to if sum(powers.values()) >= min_degree:
- Line 142: Change if max(powers.values()) >= min_degree: to if sum(powers.values()) >= min_degree:

What worked: Bug location confirmed across 3 attempts at lines 130 and 142 of sympy/polys/monomials.py. Correct fix: change max to sum. Documentation about total_degree invariant supports the fix.

What did not work: 3 research attempts (1885s + 825.4s + 726s = 2736.4s total) all reached correct diagnosis without producing code fix. Correct fix documented but not applied. Pattern of reaching correct answer but failing to implement fix persisted.

### I2 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/sympy/polys/monomials.py b/sympy/polys/monomials.py
index 0e84403307..d2cd3451e5 100755
--- a/sympy/polys/monomials.py
+++ b/sympy/polys/monomials.py
@@ -127,7 +127,7 @@ def itermonomials(variables, max_degrees, min_degrees=None):
                 for variable in item:
                     if variable != 1:
                         powers[variable] += 1
-                if max(powers.values()) >= min_degree:
+                if sum(powers.values()) >= min_degree:
                     monomials_list_comm.append(Mul(*item))
             yield from set(monomials_list_comm)
         else:
@@ -139,7 +139,7 @@ def itermonomials(variables, max_degrees, min_degrees=None):
                 for variable in item:
                     if variable != 1:
                         powers[variable] += 1
-                if max(powers.values()) >= min_degree:
+                if sum(powers.values()) >= min_degree:
                     monomials_list_non_comm.append(Mul(*item))
             yield from set(monomials_list_non_comm)
     else:
```

## Rules

### R1 — itermonomials min_degrees filter: max vs sum powers

Fix `itermonomials` in `sympy/polys/monomials.py`: change `max(powers.values())` to `sum(powers.values())` on lines 130 and 142.

**Bug**: `max(powers.values()) >= min_degree` checks the maximum single-variable exponent, not total degree. This filters out mixed monomials like `x1*x2**2` when `min_degrees=3` because their max exponent is 2.

**Fix**: Replace `max(powers.values())` with `sum(powers.values())` on both line 130 (commutative) and line 142 (non-commutative). This checks total degree (sum of exponents) against `min_degree`, matching the docstring: "min_degree <= total_degree(monom) <= max_degree".

**Impact**: `itermonomials([x1,x2,x3], 3, min_degrees=3)` changes from 3 monomials (pure cubics only) to 10 monomials (all degree-3 combos). All 11 regression tests and 1 target test pass.
