---
name: sympy-sympy-13437
description: Fix bell function to evaluate infinity correctly.
subject: sympy-sympy-13437
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add special‑case for `oo` in `bell.eval` |
| `I2` | Instructions | Naming convention for this skill |
| `R1` | Rules | Preserve existing limit handling for finite arguments |




## Instructions

### I1 — Add special‑case for `oo` in `bell.eval`

1. Open `sympy/functions/combinatorial/numbers.py`.
2. Locate the `class bell(Function):` definition and its `eval(cls, n, sym=None):` method.
3. Replace the existing limit‑check block:
   ```
-    if limit is S.Infinity:
-        return S.Infinity
   ```
   with the following check:
   ```
+    if arg is S.Infinity:
+        return S.Infinity
   ```
4. Save the file.
5. Run the test suite; `test_bell` should now pass.

This change directly returns `S.Infinity` when the argument `arg` is infinity, resolving the failing target test.

### I2 — Naming convention for this skill

Use the skill name `sympy-sympy-13437` to uniquely identify fixes related to the Sympy Bell function limit handling. Follow the pattern `<project>-<identifier>` where the identifier matches the upstream issue or test name.

## Rules

### R1 — Preserve existing limit handling for finite arguments

Do not modify the behavior of `_eval_limit` for finite `limit` values; it must continue to return `None` for non‑infinite limits as originally designed.

## References

- `skill_load(name="sympy-sympy-13437", file="LESSONS.md")` — what earlier attempts on this subject tried, and how each failed. Read it before repeating one.

