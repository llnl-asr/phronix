---
name: sympy-itermonomials-generate-filter-pattern
description: SymPy itermonomials uses generate-then-filter pattern: generates all combinations via built-in, then filters by degree constraint
metadata:
  type: reference
---

**Pattern:** The itermonomials function uses a **generate-then-filter** pattern, not early pruning during generation.

**How It Works:**

**Generation Phase (Line 123 - Commutative):**
```python
for item in combinations_with_replacement(variables, max_degree):
```
Generates ALL combinations up to max_degree, including those outside the min_degree bound.

**Example:** `itermonomials([x, y], 3, 2)`

Generates:
```
(1,1,1) → 1       (total degree 0)
(1,1,x) → x       (total degree 1)
(1,1,y) → y       (total degree 1)
(1,x,x) → x²      (total degree 2) ✓
(1,x,y) → xy      (total degree 2) ✓
(x,x,x) → x³      (total degree 3) ✓
...
```

**Filtering Phase (Lines 124-130):**
```python
powers = {}
for variable in item:
    if variable != S.One:
        powers[variable] = powers.get(variable, 0) + 1

if max(powers.values()) >= min_degree:  # BUG HERE
    monomials_list_comm.append(Mul(*item))
```

Filters out monomials that don't meet the degree constraint.

**Why This Pattern:**
1. `combinations_with_replacement` is a Python built-in - fast and correct
2. Easier to reason about: separate concerns (generation vs filtering)
3. Filter logic can be modified without changing generation

**The Bug Location:**
The bug is in the FILTER phase (line 130), not the generation phase. Generation is correct; it produces all candidates. The filter incorrectly rejects valid monomials.

**Alternative (Not Used):**
Could generate only valid-degree combinations upfront (early pruning). This would be more efficient but more complex. The research notes this as `early_pruning_generation` approach - theoretical but not implemented.

**How to Apply:**
When fixing generate-then-filter patterns:
1. Confirm generation is correct (usually is)
2. Focus on the filter condition
3. Test with candidates that should pass and should fail
4. Don't refactor generation unless there's evidence it's wrong

**For This Bug:**
- Generation: ✓ Correct (produces all combinations)
- Filtering: ❌ Wrong (uses max instead of sum)
- Fix: Change only the filter, leave generation alone
