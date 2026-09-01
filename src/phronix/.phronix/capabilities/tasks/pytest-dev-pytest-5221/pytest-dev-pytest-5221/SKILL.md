---
name: pytest-dev-pytest-5221
description: The pytest-dev-pytest-5221 subject.
subject: pytest-dev-pytest-5221
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Display fixture scope with pytest --fixtures |
| `I2` | Instructions | Instructions to solve it |
| `I3` | Instructions | Pitfalls and lessons |
| `R1` | Rules | Constraints and rules |





## Instructions

### I1 — Display fixture scope with pytest --fixtures

Display fixture scope with `pytest --fixtures`. Currently the only way to learn the scope of a fixture is to look at the docs (when documented) or at the source code. The fix adds fixture scope information (function, module, class, session, package) to the `--fixtures` output.

### I2 — Instructions to solve it

Locate the _showfixtures_main() function in src/_pytest/python.py. Find the loop that iterates over fixtures and calls tw.line(funcargspec, green=True) to display each fixture. Before that tw.line() call, add code to display the fixture scope: get the scope name from fixturedef.scope, convert to a readable string (handling enum/int values by taking the last part after splitting on "."), and output it as "    scope: <scope_name>" using tw.line(). The scope display should appear before the function argument specification for each fixture.

### I3 — Pitfalls and lessons

Pitfalls and lessons from previous attempts:
- Attempt-1 produced a massive diff that retained many functions but the scope display was added; the diff was larger than necessary
- Attempt-2 failed entirely due to an import error: "cannot import name 'Class' from '_pytest.python'" - this is a testbed environment issue, not related to the fix itself
- Attempt-3 added the scope display but the test test_show_fixtures checked for specific output patterns including 'scope: function' in the output; the format of the scope display must match what the test expects exactly
- The scope name extraction using str(fixturedef.scope).split(".")[-1] must handle both string and enum/int values for scope
- Test output showed the test was matching 'scope: function' pattern, meaning the test expected the scope to be displayed but the exact format needed to be correct
- Previous attempts show that scope display for some fixtures (like capfd, capfdbinary) was already present in the output as '[session scope]' or '[function]' - the fix should make ALL fixtures consistently show scope, not just some

## Rules

### R1 — Constraints and rules

Must not break existing fixture display format for fixtures that already have scope shown. Must handle all scope values: function, module, class, session, package. Must not modify any test files. The change must be minimal and targeted only to the fixture display logic in _showfixtures_main().

## References
