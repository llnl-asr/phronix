---
name: pytest-dev-pytest-11143
description: Fix TypeError: argument of type 'int' is not iterable when first expression in a test file is a numeric literal. The bug occurs in src/_pytest/assertion/rewrite.py where is_rewrite_disabled() is called with a value that can be an int (from item.value.value AST extraction) rather than always a string. Adding isinstance(doc, str) guard before the check fixes the issue.
subject: pytest-dev-pytest-11143
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I3` | Instructions | I7 - skill naming convention |
| `I4` | Instructions | I9 - what belongs in a skill vs memory |
| `I5` | Instructions | The patch that made the tests pass |
| `R4` | Rules | R1 - always guard is_rewrite_disabled with isinstance check |
| `R5` | Rules | R2 - regression tests must keep passing |
| `R6` | Rules | R3 - don't modify test files |

## Instructions

### I3 — I7 - skill naming convention

Skill name follows kebab-case pattern: pytest-dev-pytest-11143. A later run loads this skill by name rather than searching. The exact name determines which skill is loaded. Use name='pytest-dev-pytest-11143' so a later run calls skill_load('pytest-dev-pytest-11143') and gets this skill.

### I4 — I9 - what belongs in a skill vs memory

This skill documents: the problem symptom (TypeError with numeric first expression, pytest -k), the key insight (is_rewrite_disabled called with non-string), the exact fix (isinstance(doc, str) guard on line 681 of rewrite.py), constraints (regression tests must keep passing, don't touch other functionality), and pitfalls (what was tried and failed). This goes in the skill, NOT in memory, because a later run loads the skill first and gets all this context for free.

### I5 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/src/_pytest/assertion/rewrite.py b/src/_pytest/assertion/rewrite.py
index 157903faf..8d6fccc62 100755
--- a/src/_pytest/assertion/rewrite.py
+++ b/src/_pytest/assertion/rewrite.py
@@ -678,7 +678,7 @@ class AssertionRewriter(ast.NodeVisitor):
                 and isinstance(item.value, ast.Constant)
             ):
                 doc = item.value.value
-                if self.is_rewrite_disabled(doc):
+                if isinstance(doc, str) and self.is_rewrite_disabled(doc):
                     return
                 expect_docstring = False
             elif (
```

## Rules

### R4 — R1 - always guard is_rewrite_disabled with isinstance check

When calling is_rewrite_disabled(doc), always first check isinstance(doc, str). If doc is not a string (e.g., it's an int from AST extraction of a numeric literal), skip the check safely since a non-string cannot contain 'PYTEST_DONT_REWRITE'.

### R5 — R2 - regression tests must keep passing

The 114 regression tests in the repository must all continue to pass after the fix. Do not make any change that could cause any of these tests to fail.

### R6 — R3 - don't modify test files

Only modify src/_pytest/assertion/rewrite.py. Do not change any test files or create new test files as part of this fix.
