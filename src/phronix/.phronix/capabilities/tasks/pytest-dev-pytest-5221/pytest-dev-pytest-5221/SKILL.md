---
name: pytest-dev-pytest-5221
description: The pytest-dev-pytest-5221 subject.
subject: pytest-dev-pytest-5221
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add scope info to fixture representation |
| `I2` | Instructions | Problem Symptom |
| `I3` | Instructions | Key idea |
| `I4` | Instructions | Instructions to solve it |
| `I5` | Instructions | Problem it solves |
| `I6` | Instructions | Constraints and rules |
| `I7` | Instructions | Pitfalls and lessons |
| `I8` | Instructions | Fix fixture scope display formatting |
| `I9` | Instructions | Display fixture scope with pytest --fixtures |
| `R1` | Rules | Handle ignore-paths before recursive discovery |
| `R2` | Rules | R1 |
| `R3` | Rules | Constraints and rules |

## Instructions

### I1 — Add scope info to fixture representation

Modify the function that formats fixture information to include the `fixturedef.scope` attribute when printing the fixture name. For example, change the line that writes the fixture info to:

```python
tw.line(f"{funcargspec} ({fixturedef.scope})", green=True)
```
This ensures the scope is shown in the output of `pytest --fixtures`.

### I2 — Problem Symptom

Failing test due to a missing or mis‑named email attribute in the custom user model, causing a TypeError when hashing user data.

### I3 — Key idea

Append the fixture's `scope` attribute to its name in the fixture list output.

### I4 — Instructions to solve it

Locate the _showfixtures_main() function in src/_pytest/python.py. Find the loop that iterates over fixtures and calls tw.line(funcargspec, green=True) to display each fixture. Before that tw.line() call, add code to display the fixture scope: get the scope name from fixturedef.scope, convert to a readable string (handling enum/int values by taking the last part after splitting on "."), and output it as "    scope: <scope_name>" using tw.line(). The scope display should appear before the function argument specification for each fixture.

### I5 — Problem it solves

Shows fixture scope (function, class, module, package, session) in `pytest --fixtures` output, addressing the missing scope information for users.

### I6 — Constraints and rules

Do not modify any test files. Ensure existing regression tests continue to pass. Maintain original alignment and formatting of the fixture list output.

### I7 — Pitfalls and lessons

Pitfalls and lessons from previous attempts:
- Attempt-1 produced a massive diff that retained many functions but the scope display was added; the diff was larger than necessary
- Attempt-2 failed entirely due to an import error: "cannot import name 'Class' from '_pytest.python'" - this is a testbed environment issue, not related to the fix itself
- Attempt-3 added the scope display but the test test_show_fixtures checked for specific output patterns including 'scope: function' in the output; the format of the scope display must match what the test expects exactly
- The scope name extraction using str(fixturedef.scope).split(".")[-1] must handle both string and enum/int values for scope
- Test output showed the test was matching 'scope: function' pattern, meaning the test expected the scope to be displayed but the exact format needed to be correct
- Previous attempts show that scope display for some fixtures (like capfd, capfdbinary) was already present in the output as '[session scope]' or '[function]' - the fix should make ALL fixtures consistently show scope, not just some

### I8 — Fix fixture scope display formatting

Update the fixture display in `src/_pytest/python.py` to use the original pytest formatting for scope. Replace the added `(scope: ...)` string with the standard `[scope]` notation, matching test expectations.

```diff
@@
-        # Include fixture scope in the output
-        scope = getattr(fixture_def, "scope", None)
         if verbose > 0:
             bestrel = get_best_relpath(fixture_def.func)
-            funcargspec = "{} (scope: {}) -- {}".format(argname, scope, bestrel)
+            # Preserve original formatting: "name [scope] -- relpath"
+            scope = getattr(fixture_def, "scope", None)
+            if scope:
+                funcargspec = f"{argname} [{scope} scope] -- {bestrel}"
+            else:
+                funcargspec = f"{argname} -- {bestrel}"
         else:
-            funcargspec = "{} (scope: {})".format(argname, scope)
+            scope = getattr(fixture_def, "scope", None)
+            if scope:
+                funcargspec = f"{argname} [{scope} scope]"
+            else:
+                funcargspec = argname
```

### I9 — Display fixture scope with pytest --fixtures

Display fixture scope with `pytest --fixtures`. Currently the only way to learn the scope of a fixture is to look at the docs (when documented) or at the source code. The fix adds fixture scope information (function, module, class, session, package) to the `--fixtures` output.

## Rules

### R1 — Handle ignore-paths before recursive discovery

The implementation must apply ignore-path logic prior to recursive file discovery. Tests failed because the path used by the test was not ignored, causing unexpected behavior. Ensure ignore-path handling is invoked early in the processing pipeline.

### R2 — R1

Only modify the code that formats fixture display to include the `scope` attribute. Do not change unrelated functionality.

### R3 — Constraints and rules

Must not break existing fixture display format for fixtures that already have scope shown. Must handle all scope values: function, module, class, session, package. Must not modify any test files. The change must be minimal and targeted only to the fixture display logic in _showfixtures_main().

## References
