---
name: sympy-18057
description: The sympy-18057 subject.
subject: sympy-18057
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Problem description |
| `I2` | Instructions | Key idea |
| `I3` | Instructions | Apply fix |
| `R1` | Rules | Do not evaluate repr of non‑Expr objects |





## Instructions

### I1 — Problem description

The task addresses a failing test caused by unsafe evaluation of object representations in Sympy's equality logic, leading to an AttributeError when __repr__ of a non‑Expr object contains dot notation (e.g., 'x.y').

### I2 — Key idea

Add an early type check in __eq__ to return False for non‑Expr objects before calling sympify, preventing unsafe eval of their repr.

### I3 — Apply fix

In sympy/core/expr.py, modify __eq__:
```diff
@@
-    def __eq__(self, other):
-        try:
-            other = sympify(other)
-            if not isinstance(other, Expr):
-                return False
-        except (SympifyError, SyntaxError):
-            return False
+    def __eq__(self, other):
+        # Guard against non-Expr objects to avoid unsafe eval of their repr
+        if not isinstance(other, Expr):
+            return False
+        try:
+            other = sympify(other)
+        except (SympifyError, SyntaxError):
+            return False
```

## Rules

### R1 — Do not evaluate repr of non‑Expr objects

__eq__ must return False for objects that are not instances of Expr without calling sympify on them.

## References

- `skill_load(name="sympy-18057", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

