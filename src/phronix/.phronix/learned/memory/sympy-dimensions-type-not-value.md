---
name: sympy-dimensions-type-not-value
description: Transcendental function return dimensions are type-based, not value-dependent
metadata:
  type: lesson
---

**Symptom**: Considering whether the return dimension of transcendental functions depends on the specific numeric value of the argument.

**Root Cause**: Dimensional analysis is a type system that operates independently of numeric values. The dimension of a result depends only on:
1. The operation being performed
2. Whether arguments are dimensionless or dimensional

The actual numeric value (e.g., 1.5 vs 3.7) has no effect on dimensional analysis.

**Fix**: For transcendental functions, return dimension is determined solely by:
- Function type (is it transcendental?)
- Argument dimension status (dimensionless or not?)

Never by the actual numeric value.

**Why**: This hypothesis was ruled out during return-value-handling investigation for sympy issue 24066. Dimension checking is static type analysis, not value-dependent computation.

**Related**: [[sympy-transcendental-functions-dimensionless]]
