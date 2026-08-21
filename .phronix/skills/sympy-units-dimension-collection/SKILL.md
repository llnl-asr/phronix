---
name: sympy-units-dimension-collection
description: Where the dimensionless-exponent-in-Function bug lives and why
subject: sympy-units-dimension-collection
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `R1` | Rules | Do not make the Function branch require all args dimensionless |
| `X1` | References | Root cause of sympy-24066: Function branch lacks Pow branch's dimensionless check |
| `X2` | References | Existing test coverage gap for the dimensionless-Function case |




## Instructions

## Rules

### R1 — Do not make the Function branch require all args dimensionless

When fixing the Function-branch dimensionless bug in UnitSystem._collect_factor_and_dimension, only coerce args whose dimension IS dimensionless (via is_dimensionless()) to Dimension(1); leave non-dimensionless args' dimensions unchanged. Do NOT add a strict check that raises when a Function's argument dimension is not dimensionless — sympy/physics/units/tests/test_quantities.py::test_factor_and_dimension (~line 353-356) asserts `SI._collect_factor_and_dimension(exp(pH)) == (1, volume/amount_of_substance)` where pH = -log(cH) and cH has dimension amount_of_substance/volume (not dimensionless). A strict version breaks this existing, currently-passing test. See refuted approach [[raise-on-non-dimensionless-function-arg]] and working approach [[coerce-dimensionless-in-function-branch]].

## References

### X1 — Root cause of sympy-24066: Function branch lacks Pow branch's dimensionless check

In sympy/physics/units/unitsystem.py, UnitSystem._collect_factor_and_dimension has a generic `Function` branch (~lines 192-196) that returns `(expr.func(*factors), *(d[1] for d in fds))` for each arg's dimension verbatim — it never calls `self.get_dimension_system().is_dimensionless(...)` on arg dimensions. The `Pow` branch just above it (~lines 167-172) DOES call is_dimensionless() on the exponent's dimension and coerces to Dimension(1) when true. This asymmetry is the root cause: a Function (exp/log/etc.) applied to a dimensionless-but-not-literal-Dimension(1) argument (e.g. built from unit ratios like second/(farad*ohm)) keeps its non-trivial Dimension object, which then fails `==` against Dimension(1) in the Add branch and raises ValueError.

### X2 — Existing test coverage gap for the dimensionless-Function case

sympy/physics/units/tests/test_quantities.py has three tests touching _collect_factor_and_dimension's Function/Pow handling: test_factor_and_dimension (general coverage, includes the non-dimensionless exp(pH) case above), test_issue_22164 (Pow with Quantity base/exponent, doesn't hit the Function branch), and test_issue_20288 (`1 + exp(u**2/v**2)` where u,v share dimension energy — u**2/v**2 already collapses to literal Dimension(1) via Pow/Mul BEFORE reaching the Function branch, so it currently passes but does NOT exercise the bug). None of these cover a Function applied to an argument that is dimensionless via is_dimensionless() but not the literal Dimension(1) object (e.g. second/(farad*ohm)), nor an Add combining Dimension(1) with a Function of such an argument — which is exactly the sympy-24066 issue repro. A new test covering this case is needed; test_issue_20288 is the closest existing analog but insufficient.
