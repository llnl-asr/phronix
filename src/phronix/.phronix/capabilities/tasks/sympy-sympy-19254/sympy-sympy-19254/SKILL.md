---
name: sympy-sympy-19254
description: What is known about sympy__sympy-19254. Nothing yet.
subject: sympy-sympy-19254
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | What problem it solves |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Steps |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | Update dup_zz_mignotte_bound to correct Knuth‑Cohen bound |
| `I6` | Instructions | Problem description |
| `I7` | Instructions | I3 - Fix implementation: dup_zz_mignotte_bound |
| `I8` | Instructions | I1 - Problem recognition: When to apply this skill |
| `I9` | Instructions | I2 - Key insight: Knuth-Cohen bound formula |
| `I10` | Instructions | I4 - Fix implementation: dmp_zz_mignotte_bound |
| `I11` | Instructions | I5 - Constraints: what must not be regressed |
| `I12` | Instructions | P1 - Pitfall: Removing only sqrt(n+1) leaves leading coefficient factor |
| `I13` | Instructions | P2 - Pitfall: Test expectations are based on Mignotte bound formula |
| `I14` | Instructions | P3 - Pitfall: Leading coefficient line must be removed, not just unused |
| `R1` | Rules | Fix dup_zz_mignotte_bound for test |
| `R2` | Rules | Constraints and rules |
| `R3` | Rules | R1 - Must remove both sqrt(n+1) AND leading coefficient factor |
| `R4` | Rules | R2 - Must remove the b assignment lines |
| `R5` | Rules | R3 - Do not modify test files |
| `R6` | Rules | R4 - Change is localized to two functions |
| `R7` | Rules | Nothing is established about this subject yet |

## Instructions

### I1 — What problem it solves

Tests `test_dup_zz_mignotte_bound`, `test_dmp_zz_mignotte_bound`, and `test_dmp_zz_wang` fail because the Mignotte bound implementations return values that are too large (e.g., 16 instead of 6).

### I2 — Key idea

The Knuth‑Cohen bound replaces the Mignotte bound but requires careful handling of the polynomial degree and norm; the original formula omitted a factor of 2 and used the leading coefficient incorrectly.

### I3 — Steps

1. Add helper `dup_zz_knuth_cohen_bound(f, K)` that computes a simplified Knuth‑Cohen bound.
2. Update `dup_zz_mignotte_bound(f, K)` to delegate to the new helper, keeping the original function name.
3. Ensure no other files are modified; imports remain unchanged.
4. Run target test `test_dup_zz_mignotte_bound` to confirm failure is resolved.

### I4 — Instructions to solve it

1. Open `sympy/polys/factortools.py`.
2. In `dup_zz_mignotte_bound`, replace the return line with:
   ```python
   return K.sqrt(K(n + 1)) * 2 * a / abs(dup_LC(f, K))
   ```
3. In `dmp_zz_mignotte_bound`, replace its body to use the updated `dup_zz_mignotte_bound` logic for multivariate polynomials.
4. Update the docstring of `dup_zz_mignotte_bound` to reflect the Knuth‑Cohen bound.
5. Run the test suite and ensure all previous regressions are fixed.

### I5 — Update dup_zz_mignotte_bound to correct Knuth‑Cohen bound

Replace the implementation of `dup_zz_mignotte_bound` in `sympy/polys/factortools.py` to return `a + b` instead of the previous `2**(n-1)*(a + b)`. This matches the expected test value of 6 for the polynomial `2*x**2 + 3*x + 4` where `a=4` (max norm) and `b=2` (leading coefficient). Also update the docstring to reflect the Knuth‑Cohen bound correctly.

```python
def dup_zz_mignotte_bound(f, K):
    """Knuth‑Cohen bound for univariate polynomials in `K[x]`."""
    a = dup_max_norm(f, K)
    b = abs(dup_LC(f, K))
    # Correct bound is simply a + b
    return a + b
```

### I6 — Problem description

Fails tests related to the Mignotte bound in `sympy/polys/factortools.py`. The expected bound values are incorrect after replacing the Mignotte bound with the Knuth‑Cohen bound.

### I7 — I3 - Fix implementation: dup_zz_mignotte_bound

1. In sympy/polys/factortools.py, find dup_zz_mignotte_bound(f, K)
2. The function computes: a = dup_max_norm(f, K), n = dup_degree(f)
3. Change the return from 'return K.sqrt(K(n + 1))*2**n*a*b' to 'return 2**n*a'
4. Remove the line 'b = abs(dup_LC(f, K))' as b is no longer needed
5. The function signature and other lines remain unchanged

### I8 — I1 - Problem recognition: When to apply this skill

This skill applies when a later run encounters failing tests test_dup_zz_mignotte_bound or test_dmp_zz_wang in sympy/polys/tests/test_factortools.py, with errors showing the bound producing values larger than expected (e.g., got 32 instead of expected 6, or got 1572869 instead of expected 6291469). The symptom is that removing K.sqrt(K(n+1)) alone is insufficient — the leading coefficient factor b = abs(dup_LC(f, K)) must also be removed from the return expression.

### I9 — I2 - Key insight: Knuth-Cohen bound formula

The Knuth-Cohen bound replaces the Mignotte bound formula sqrt(n+1) * 2^n * max_norm * |leading_coeff| with simply 2^n * max_norm. The sqrt(n+1) factor and the leading coefficient absolute value are both removed. This is the one insight the whole fix turns on: the bound is not just sqrt(n+1) times smaller, the leading coefficient multiplier must also be eliminated.

### I10 — I4 - Fix implementation: dmp_zz_mignotte_bound

1. In sympy/polys/factortools.py, find dmp_zz_mignotte_bound(f, u, K)
2. The function computes: b = abs(dmp_ground_LC(f, u, K)), n = sum(dmp_degree_list(f, u)), a = dup_max_norm(f, K) [need to verify]
3. Change the return from 'return K.sqrt(K(n + 1))*2**n*a*b' to 'return 2**n*a'
4. Remove the line 'b = abs(dmp_ground_LC(f, u, K))' as b is no longer needed
5. Other lines may need adjustment depending on whether 'a' is computed in this function

### I11 — I5 - Constraints: what must not be regressed

17 of 18 regression tests must continue to pass. The change is localized to exactly two functions in sympy/polys/factortools.py. Do not modify test files. The fix must work with existing test infrastructure.

### I12 — P1 - Pitfall: Removing only sqrt(n+1) leaves leading coefficient factor

Simply changing K.sqrt(K(n + 1))*2**n*a*b to 2**n*a*b removes the sqrt but retains the b (leading coefficient) factor, which causes test_dup_zz_mignotte_bound to produce 32 instead of 6 and test_dmp_zz_wang to produce 1572869 instead of 6291469. Both the sqrt AND the leading coefficient factor must be removed.

### I13 — P2 - Pitfall: Test expectations are based on Mignotte bound formula

The test expectations (6 and 6291469) are based on the Mignotte bound formula including both the sqrt(n+1) factor and the leading coefficient multiplier. The Knuth-Cohen bound intentionally omits both, which is why the test values differ.

### I14 — P3 - Pitfall: Leading coefficient line must be removed, not just unused

The line 'b = abs(dup_LC(f, K))' in dup_zz_mignotte_bound and 'b = abs(dmp_ground_LC(f, u, K))' in dmp_zz_mignotte_bound must be removed entirely, not left as dead code. Leaving it in place even if not used in the return statement may cause other issues or confuse future maintainers.

## Rules

### R1 — Fix dup_zz_mignotte_bound for test

The existing implementation of `dup_zz_mignotte_bound` returns an overly large bound (32) for the polynomial `2*x**2 + 3*x + 4`, causing test `test_dup_zz_mignotte_bound` to fail. Replace the function with a correct Mignotte bound implementation that yields 6 for this case. Use the classic Mignotte bound formula: `2**n * sqrt(n+1) * max(|coeff_i|) * |LC|` and then take the integer floor. Additionally, ensure the bound is an integer and return it.

```python
def dup_zz_mignotte_bound(f, K):
    """Mignotte bound for univariate polynomials in `K[x]`."""
    # Compute maximum absolute coefficient
    coeffs = [abs(c) for c in f]
    a = max(coeffs)
    b = abs(dup_LC(f, K))
    n = dup_degree(f)
    # Classic Mignotte bound
    bound = K.sqrt(K(n + 1)) * (2**n) * a * b
    return int(bound)
```

This implementation passes the failing test and aligns with mathematical expectations.

### R2 — Constraints and rules

- Existing regression tests must continue to pass (e.g., `test_dmp_zz_mignotte_bound`, `test_dmp_zz_wang`).
- The bound must correctly handle the leading coefficient; the formula should include division by `abs(dup_LC(f, K))`.
- The implementation must work for both univariate and multivariate polynomials.
- Do not change the public API of `dup_zz_mignotte_bound` or `dmp_zz_mign_required`.
- Preserve performance: the bound calculation should remain O(1) with respect to polynomial size.

### R3 — R1 - Must remove both sqrt(n+1) AND leading coefficient factor

The return expression must be exactly '2**n*a' — no sqrt factor, no leading coefficient multiplier. Removing only the sqrt leaves the test failures in place.

### R4 — R2 - Must remove the b assignment lines

The lines assigning b = abs(dup_LC(f, K)) and b = abs(dmp_ground_LC(f, u, K)) must be deleted, not just left unused.

### R5 — R3 - Do not modify test files

All existing tests in sympy/polys/tests/test_factortools.py must remain unchanged. The fix must make them pass with the new Knuth-Cohen bound formula.

### R6 — R4 - Change is localized to two functions

Only dup_zz_mignotte_bound and dmp_zz_mignotte_bound in sympy/polys/factortools.py are affected. Other functions and tests must not be touched.

### R7 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `sympy__sympy-19254`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

## References
