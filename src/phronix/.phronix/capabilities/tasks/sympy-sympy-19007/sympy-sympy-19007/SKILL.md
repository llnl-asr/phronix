---
name: sympy-sympy-19007
description: Research on learning reconcile. Covers is the reconciliation framework properly configured; are aspects properly defined for the topic; are approaches recorded and measurable. Approaches tried: reconcile framework setup, A2.
subject: sympy-sympy-19007
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Apply fix |

## Instructions

### I1 — Problem description

When accessing an element of a BlockMatrix with a symbolic row index, e.g., C[i,0] where i is symbolic, the code incorrectly simplifies to the first block (A) regardless of which block the index refers to. This leads to wrong matrix element retrieval when the BlockMatrix contains multiple blocks of differing row sizes.

### I2 — Key idea

Detect symbolic indices in BlockMatrix._entry and return the unevaluated BlockMatrix when the index is not a concrete integer, avoiding premature simplification.

### I3 — Apply fix

1. Open `sympy/matrices/expressions/blockmatrix.py`.
2. In the `_entry` method, add a check at the start:
   ```
   if not (hasattr(i, 'is_Integer') and i.is_Integer and hasattr(j, 'is_Integer') and j.is_Integer):
       return self
   ```
3. Update the subsequent block selection logic to use simple integer comparisons:
   replace `if (i < numrows) != False:` with `if i < numrows:` and similarly for `j`.
4. Save the file.
5. Run the test suite for BlockMatrix to ensure all existing tests pass.

## References

### X1 — Where research on this subject stands

State of research on this subject as of the last stage that ran.

Measured by **reconcile methodology** (max, target 1.0).

**Established**
- reconcile-framework-setup (working)
- A2 (working)

**Still open**
- aspect not yet answered: framework
- aspect not yet answered: aspects
- aspect not yet answered: approaches
- aspect not yet answered: reconciliation
- aspect not yet answered: learner-improvement

**Where the detail is**
- reconcile-framework-setup: reconcile skill load (phronix-learning-reconcile)
- A2: phronix-learning-reconcile skill load; research observations recorded
- full record: research topic `learning-reconcile` (via research_status, only if this summary is not enough)
