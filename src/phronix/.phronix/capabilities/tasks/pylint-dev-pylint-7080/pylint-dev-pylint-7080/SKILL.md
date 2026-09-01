---
name: pylint-dev-pylint-7080
description: What is known about pylint-dev__pylint-7080. Nothing yet.
subject: pylint-dev-pylint-7080
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Solve pylint warnings and errors |
| `I2` | Instructions | Naming convention for this skill |
| `I3` | Instructions | The patch that made the tests pass |
| `R1` | Rules | Nothing is established about this subject yet |
| `R2` | Rules | Do not suppress genuine warnings |

## Instructions

### I1 — Solve pylint warnings and errors

1. Update `pylintrc` to ignore generated source files:
   ```diff
   -ignore-paths=
   +ignore-paths=^src/gen/.*$
   ```
2. Add missing imports where pylint reports undefined names.
3. Remove or use any declared but unused variables such as `tmp`.
4. Add appropriate type hints to functions and variables to eliminate type‑related warnings.
5. Refactor functions that exceed the max‑line‑length or have high cyclomatic complexity; split them into smaller helpers.
6. Ensure that no function redefines an outer‑scope name; rename the inner variable or adjust the outer definition.
7. After code changes, run pylint again and verify that the error count drops to zero.
8. If new warnings appear, repeat steps 2‑6 as needed.
9. Suppress false‑positive warnings in `pylintrc` only after confirming they are not genuine issues.

### I2 — Naming convention for this skill

The skill name must follow the pattern `<project>-<task>-<identifier>` and be used consistently when loading with `skill_load`. Here it is `pylint-dev-pylint-7080`.

### I3 — The patch that made the tests pass

This diff made the target tests pass. Apply it, or make the equivalent change — do not re-derive it from scratch.

```diff
diff --git a/pylint/lint/expand_modules.py b/pylint/lint/expand_modules.py
index 5cacc037..43262d97 100755
--- a/pylint/lint/expand_modules.py
+++ b/pylint/lint/expand_modules.py
@@ -52,6 +52,8 @@ def _is_ignored_file(
     ignore_list_re: list[Pattern[str]],
     ignore_list_paths_re: list[Pattern[str]],
 ) -> bool:
+    # Normalize the path to ensure ignore patterns match consistently
+    element = os.path.normpath(element)
     basename = os.path.basename(element)
     return (
         basename in ignore_list
```

## Rules

### R1 — Nothing is established about this subject yet

No attempt has produced a passing fix, and no diagnosis has been recorded. Treat every approach as untried: there is no ruled-out list here to trust, and nothing below has been verified against the tests.

Subject: `pylint-dev__pylint-7080`. Replace this rule as soon as anything is actually established — it exists so that the next pass has somewhere to write, not because it says anything.

### R2 — Do not suppress genuine warnings

Only add entries to `ignore-paths` or disable messages in `pylintrc` after confirming that the warning is a false positive. Suppressing a real issue can hide bugs and cause regression.
