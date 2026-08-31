---
name: django-django-14155
description: The test-tracker subject.
subject: django-django-14155
type: skill
---

## Index

| Label | Section | Covers |
| --- | --- | --- |
| `I1` | Instructions | Update __repr__ in django/urls/resolvers.py |
| `I2` | Instructions | I7 — Problem description |
| `I3` | Instructions | I9 — Skill vs Memory |
| `I4` | Instructions | Correct __repr__ handling for functools.partial |
| `I5` | Instructions | Problem solved |
| `I6` | Instructions | Key idea |
| `I7` | Instructions | Instructions to solve it |
| `I8` | Instructions | Naming convention for this skill |
| `I9` | Instructions | Problem: AxesGrid GeoAxes TypeError |
| `R1` | Rules | Only change __repr__ |
| `R2` | Rules | Constraints and rules |
| `R3` | Rules | Do not alter ordering or quoting of partial arguments |

## Instructions

### I1 — Update __repr__ in django/urls/resolvers.py

Modify ResolverMatch.__repr__ to detect functools.partial and represent it as the partial object itself, preserving original formatting expected by tests. Use the following implementation:
```python
def __repr__(self):
    if isinstance(self.func, functools.partial):
        func_repr = repr(self.func)
        return (
            "ResolverMatch(func=%s, args=%s, kwargs=%s, url_name=%s, "
            "app_names=%s, namespaces=%s, route=%s)" % (
                func_repr, self.args, self.kwargs, self.url_name,
                self.app_names, self.namespaces, self.route,
            )
        )
    return "ResolverMatch(func=%s, args=%s, kwargs=%s, url_name=%s, app_names=%s, namespaces=%s, route=%s)" % (
        self._func_path, self.args, self.kwargs, self.url_name,
        self.app_names, self.namespaces, self.route,
    )
```

### I2 — I7 — Problem description

The task fails with a TypeError because a custom user model does not have an `email` attribute, yet code accesses `user.email`. This manifests when email handling code runs, causing test failures.

### I3 — I9 — Skill vs Memory

Use this skill to capture enduring knowledge about the problem and its fix. Store transient observations, test output snippets, and one‑off experiment details in memories instead; only the abstract solution, invariant constraints, and reusable patterns belong in the skill.

### I4 — Correct __repr__ handling for functools.partial

Update `ResolverMatch.__repr__` in `django/urls/resolvers.py` to correctly represent `functools.partial` objects. The new implementation:
```python
import functools

class ResolverMatch:
    ...
    def __repr__(self):
        if isinstance(self.func, functools.partial):
            func_repr = repr(self.func)
            return (
                "ResolverMatch(func=%s, args=%s, kwargs=%s, url_name=%s, "
                "app_names=%s, namespaces=%s, route=%s)" % (
                    func_repr, self.args, self.kwargs, self.url_name,
                    self.app_names, self.namespaces, self.route,
                )
            )
        return "ResolverMatch(func=%s, args=%s, kwargs=%s, url_name=%s, app_names=%s, namespaces=%s, route=%s)" % (
            self._func_path, self.args, self.kwargs, self.url_name,
            self.app_names, self.namespaces, self.route,
        )
```

### I5 — Problem solved

Failing tests for `ResolverMatch.__repr__` when the view is a `functools.partial` instance. The symptom is that the representation shows the function as `functools.partial(...)` instead of the underlying view name and arguments.

### I6 — Key idea

Unwrap `functools.partial` objects to obtain the real view function before generating the `ResolverMatch` representation.

### I7 — Instructions to solve it

1. Open `django/urls/resolvers.py`.
2. Locate the `ResolverMatch.__init__` method.
3. After the line where `func` is received (typically near the top of the method), insert:
   ```python
   # Unwrap functools.partial to get the underlying function
   if isinstance(func, functools.partial):
       func = func.func
   ```
4. Ensure this block appears **before** the existing check `if not hasattr(func, '__name__'):`.
5. Save the file and run the target test suite.
6. Verify that all three failing tests (`test_repr`, `test_repr_functools_partial`, `test_resolver_match_on_request`) now pass while the regression suite remains green.

### I8 — Naming convention for this skill

Use the exact skill name `django-django-14155` when creating or referencing this skill. The `skill_load("phronix-learn-from-attempt")` method will locate this skill by that name.

All future runs should refer to this skill by this slug to ensure they load the correct instructions and rules.

### I9 — Problem: AxesGrid GeoAxes TypeError

Creating AxesGrid with cartopy GeoAxes as axis_class raises TypeError: 'method' object is not subscriptable. The _tick_only function in axes_grid.py assumes ax.axis supports dict-style access with string keys, but this only works for custom Axes with AxisDict, not GeoAxes where axis is a method.

## Rules

### R1 — Only change __repr__

Do not modify other parts of resolvers.py to avoid regressions.

### R2 — Constraints and rules

- Do not modify any other part of `ResolverMatch.__init__`.
- Regression tests must remain green (89/89). 
- Preserve handling of class‑based views and normal functions.
- `functools` is already imported; do not add new imports.
- The unwrapping must occur before the `hasattr(func, '__name__')` check.

### R3 — Do not alter ordering or quoting of partial arguments

The representation must match Django's expected string exactly, including the order of `partial_args` and `partial_kwargs` and their quoting. Any deviation will cause test failures.

## References
