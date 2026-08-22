---
name: pallets-flask-4045
description: Fixing pallets__flask-4045 (raise error when Blueprint name contains a dot, since dots are significant for nested blueprints).
subject: pallets-flask-4045
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Add the Blueprint name dot-check in __init__ |
| `R1` | Rules | Verify the specific target test in isolation, not the whole suite |
| `R2` | Rules | The __init__ dot-check alone does not close this task — second target test still unexplained |




## Instructions

### I1 — Add the Blueprint name dot-check in __init__

In `src/flask/blueprints.py`, inside `Blueprint.__init__`, right after the `super().__init__(...)` call and before `self.name = name`, add:

```python
if "." in name:
    raise ValueError("'name' may not contain a dot '.' character.")
```

This mirrors the existing dot check for endpoint names. It correctly fixes the name-validation target test on its own, but is NOT sufficient to close this task — see the rule about the second target test.

## Rules

### R1 — Verify the specific target test in isolation, not the whole suite

Run `pytest tests/test_blueprints.py::test_route_decorator_custom_endpoint_with_dots -q` alone before drawing any conclusion. Do not run broad suites like test_basic.py for this task — they fail in this environment with unrelated `DeprecationWarning: werkzeug.urls.url_parse is deprecated` errors (werkzeug/environment version mismatch, nothing to do with blueprints). A prior attempt read that noise, concluded "environment issue unrelated to fix," and never saw the real traceback for the target test it needed to fix. Never dismiss a target test's failure as "environment issue" without having actually run and read that test's own traceback in isolation.

### R2 — The __init__ dot-check alone does not close this task — second target test still unexplained

This task has TWO target tests. Only the `__init__` dot-check (see I1) was applied and verified in the one recorded attempt; `tests/test_blueprints.py::test_route_decorator_custom_endpoint_with_dots` still failed afterward, and the real cause was never diagnosed (the attempt stopped after misreading unrelated suite noise as an environment issue — see R1). An assert for dots in `endpoint`/`view_func.__name__` already appears to exist in `Blueprint.add_url_rule` (src/flask/blueprints.py, non-deferred, called directly from `route()`), so why the isolated test still fails is an open question for the next attempt — read that test's actual traceback (per R1) to find out, don't assume the existing assert is sufficient or that it's already broken.

## References
