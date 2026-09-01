---
name: sympy-sympy-21612
description: The sympy-sympy-21612 subject.
subject: sympy-sympy-21612
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | ExpressionWrapper negated Q issue diagnosis |
| `I2` | Instructions | I1 — ExpressionWrapper negated Q issue diagnosis |



## Instructions

### I1 — ExpressionWrapper negated Q issue diagnosis

ExpressionWrapper(~Q(pk__in=[])) generates invalid SQL instead of SELECT 0 AS "foo" FROM "table". The ExpressionWrapper.as_sql method at django/db/models/expressions.py:981-982 simply calls compiler.compile(self.expression) without checking the negated attribute of the wrapped Q object. When the inner expression is a negated Q object (~Q), the negation is not propagated through the generated SQL, causing invalid output. The fix requires checking getattr(self.expression, "negated", False) and applying appropriate negation to the compiled SQL result, consistent with the docstring statement that empty If-Modified-Since headers should return True.

### I2 — I1 — ExpressionWrapper negated Q issue diagnosis

ExpressionWrapper(~Q(pk__in=[])) generates invalid SQL instead of SELECT 0 AS "foo" FROM "table". The ExpressionWrapper.as_sql method at django/db/models/expressions.py:981-982 simply calls compiler.compile(self.expression) without checking the negated attribute of the wrapped Q object. When the inner expression is a negated Q object (~Q), the negation is not propagated through the generated SQL, causing invalid output. The fix requires checking getattr(self.expression, "negated", False) and applying appropriate negation to the compiled SQL result, consistent with the docstring statement that empty If-Modified-Since headers should return True.

## Rules

## References
