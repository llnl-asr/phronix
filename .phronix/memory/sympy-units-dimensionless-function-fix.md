---
name: sympy-units-dimensionless-function-fix
description: SymPy issue 24066: SI._collect_factor_and_dimension Function handler doesn't validate dimensionless arguments for transcendental functions
metadata:
  type: lesson
---

**Symptom**: ValueError: Dimension of "exp(second/(farad*ohm))" is Dimension(time/(capacitance*impedance)), but it should be Dimension(1) when processing expressions like `100 + exp(dimensionless_expr)`.

**Root Cause**: The Function handler in UnitSystem._collect_factor_and_dimension() (unitsystem.py lines 192-196) returns argument dimensions directly without checking if transcendental functions require dimensionless arguments.

**Fix**: Check if function is instance of ExpBase, TrigonometricFunction, InverseTrigonometricFunction, HyperbolicFunction, or InverseHyperbolicFunction. For these functions:
1. Validate all arguments are dimensionless using is_dimensionless()
2. Raise ValueError if not
3. Return Dimension(1) if valid

Follow the pattern already used in the Pow handler (lines 170-172).

**Why**: Transcendental functions mathematically require dimensionless arguments due to Taylor series constraints. SymPy's class hierarchy correctly identifies these function types.

**Related**: 
- Prior fix attempt (commit b3d17030b8) only fixed a syntax bug, not the semantic issue
- Test test_issue_20288 shows expected behavior
- Skill: [[sympy-units-dimensionless-functions]]
